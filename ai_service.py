"""
AI 服务 - 改造为融合傻酒馆角色卡 + 世界书 + 经历的 Prompt 生成
"""
import os
import re
import random
import json
import httpx
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from database import Character, Experience, User, WorldBook, LoreEntry, CharacterWorldBook, ConversationSummary, UserMemory

# AI API 配置 - 从环境变量读取
AI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_API_BASE = os.getenv("OPENAI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
AI_MODEL = os.getenv("AI_MODEL", "qwen-plus")


def _get_bound_worldbooks(character_id: int, db: Session) -> List[WorldBook]:
    """获取角色绑定的世界书"""
    bindings = db.query(CharacterWorldBook).filter(
        CharacterWorldBook.character_id == character_id
    ).all()
    
    worldbook_ids = [b.worldbook_id for b in bindings]
    if not worldbook_ids:
        return []
    
    return db.query(WorldBook).filter(WorldBook.id.in_(worldbook_ids)).all()


def _scan_lore_entries(
    worldbooks: List[WorldBook],
    chat_history: List[str],
    db: Session
) -> Tuple[List[str], List[str]]:
    """
    扫描聊天历史，激活匹配的世界书条目
    返回 (before_char_entries, after_char_entries)
    """
    # 合并所有世界书的条目
    all_entries = []
    for wb in worldbooks:
        for entry in wb.entries:
            if not entry.enabled:
                continue
            all_entries.append((wb, entry))
    
    if not all_entries:
        return [], []
    
    # 构建扫描文本（最近的聊天消息）
    scan_text = '\n'.join(chat_history[-50:])  # 默认扫描最近50条
    
    activated = []
    
    for wb, entry in all_entries:
        # 常驻条目始终激活
        if entry.constant:
            activated.append(entry)
            continue
        
        # 确定扫描深度
        depth = entry.scan_depth if entry.scan_depth > 0 else wb.scan_depth
        scan_messages = chat_history[-depth:] if depth > 0 else chat_history
        entry_scan_text = '\n'.join(scan_messages)
        
        # 检查主关键词匹配
        keys = [k.strip() for k in entry.keys.split(',') if k.strip()]
        if not keys:
            continue
        
        primary_match = _check_keys_match(
            keys, entry_scan_text, 
            entry.case_sensitive, entry.use_regex
        )
        
        if not primary_match:
            continue
        
        # 选择性模式：需要同时匹配次要关键词
        if entry.selective:
            secondary_keys = [k.strip() for k in entry.secondary_keys.split(',') if k.strip()]
            if secondary_keys:
                secondary_match = _check_keys_match(
                    secondary_keys, entry_scan_text,
                    entry.case_sensitive, entry.use_regex
                )
                if not secondary_match:
                    continue
        
        # 概率检查
        if entry.probability < 100:
            if random.randint(1, 100) > entry.probability:
                continue
        
        activated.append(entry)
    
    # 按优先级排序（高优先级在前），同优先级按 insertion_order 排序
    activated.sort(key=lambda e: (-e.priority, e.insertion_order))
    
    # 按 position 分组
    before_char = []
    after_char = []
    for entry in activated:
        if entry.position == 'after_char':
            after_char.append(entry.content)
        else:
            before_char.append(entry.content)
    
    return before_char, after_char


def _check_keys_match(keys: List[str], text: str, case_sensitive: bool, use_regex: bool) -> bool:
    """检查关键词是否在文本中匹配"""
    for key in keys:
        if not key:
            continue
        
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                if re.search(key, text, flags):
                    return True
            except re.error:
                # 正则表达式错误，回退到普通匹配
                if case_sensitive:
                    if key in text:
                        return True
                else:
                    if key.lower() in text.lower():
                        return True
        else:
            if case_sensitive:
                if key in text:
                    return True
            else:
                if key.lower() in text.lower():
                    return True
    
    return False


def _get_recent_experiences(character_id: int, db: Session, limit: int = 7) -> List[Experience]:
    """获取角色最近的经历"""
    return db.query(Experience).filter(
        Experience.character_id == character_id
    ).order_by(Experience.date.desc()).limit(limit).all()


def generate_character_prompt(
    character: Character,
    user: User,
    db: Session,
    chat_history: Optional[List[str]] = None
) -> str:
    """
    生成完整的系统提示词
    融合: 角色卡 system_prompt + 世界书 + 角色描述 + 经历 + 亲密度 + 摘要 + 用户记忆
    """
    if chat_history is None:
        chat_history = []
    
    parts = []
    
    # 1. 世界书 before_char 条目
    worldbooks = _get_bound_worldbooks(character.id, db)
    before_char_entries, after_char_entries = _scan_lore_entries(worldbooks, chat_history, db)
    
    if before_char_entries:
        parts.append("【世界知识】\n" + '\n'.join(before_char_entries))
    
    # 2. 对话摘要（长期记忆）
    summary_text = get_summaries_for_context(user.id, character.id, db, limit=3)
    if summary_text:
        parts.append(summary_text)
    
    # 3. 用户记忆（关键信息）
    memory_text = get_user_memories_for_context(user.id, character.id, db, limit=10)
    if memory_text:
        parts.append(memory_text)
    
    # 4. 角色卡 system_prompt（如果有的话，作为最高优先级的系统指令）
    if character.system_prompt:
        # 替换傻酒馆占位符
        sys_prompt = character.system_prompt
        sys_prompt = sys_prompt.replace('{{char}}', character.name)
        sys_prompt = sys_prompt.replace('{{user}}', user.username)
        parts.append(sys_prompt)
    
    # 5. 角色描述和设定
    char_desc_parts = []
    
    if character.description:
        char_desc_parts.append(f"【角色描述】\n{character.description}")
    
    if character.personality:
        char_desc_parts.append(f"【性格特征】\n{character.personality}")
    
    # 兼容旧字段
    if character.background and not character.description:
        char_desc_parts.append(f"【生平背景】\n{character.background}")
    if character.habits and not character.personality:
        char_desc_parts.append(f"【回复习惯】\n{character.habits}")
    if character.world_view and not character.scenario:
        char_desc_parts.append(f"【世界观】\n{character.world_view}")
    
    if character.scenario:
        char_desc_parts.append(f"【场景设定】\n{character.scenario}")
    
    if char_desc_parts:
        parts.append('\n'.join(char_desc_parts))
    
    # 6. 世界书 after_char 条目
    if after_char_entries:
        parts.append("【补充设定】\n" + '\n'.join(after_char_entries))
    
    # 7. 对话示例
    if character.mes_example:
        # 清理 <START> 标记
        examples = character.mes_example.replace('<START>', '').strip()
        if examples:
            parts.append(f"【对话示例】\n{examples}")
    
    # 8. 最近经历
    recent_experiences = _get_recent_experiences(character.id, db)
    if recent_experiences:
        exp_text = "【最近的经历】\n"
        for exp in reversed(recent_experiences):
            date_str = exp.date.strftime("%Y-%m-%d")
            exp_text += f"- {date_str}: {exp.content}\n"
        parts.append(exp_text)
    
    # 9. 亲密度和互动指引
    parts.append(f"""【当前状态】
- 与用户({user.username})亲密度: {user.intimacy:.1f}/100
- 亲密度越高，关系越亲密，语气越自然亲近

【回复风格要求 - 必须严格遵守】
1. 模仿微信聊天风格，简洁自然，像日常对话
2. 回复要简短，通常1-3句话，不超过50字
3. 绝对禁止括号内的动作描述（如"（轻轻擦着酒杯）"、"(微笑)"等任何括号形式）
4. 绝对禁止场景描写（如"酒馆里"、"窗外阳光"等）
5. 绝对禁止心理描写（如"心里想着"、"暗暗决定"等）
6. 只输出纯对话文字，像真人发微信一样
7. 可以用表情符号，但不要过度
8. 根据亲密度调整语气：低亲密度礼貌，高亲密度亲密

【错误示例 - 绝对不要这样回复】
- （微笑）你好呀～ → ❌ 有括号动作
- 嗯...（低头想了想）好吧 → ❌ 有括号动作
- 阳光洒进酒馆，她抬起头说... → ❌ 有场景描写

【正确示例】
- 好呀～在干嘛呢？😊
- 哈哈，真的吗？
- 嗯嗯，我知道啦
- 那你呢？最近怎么样？""")
    
    # 10. post_history_instructions（如果有）
    if character.post_history_instructions:
        phi = character.post_history_instructions
        phi = phi.replace('{{char}}', character.name)
        phi = phi.replace('{{user}}', user.username)
        parts.append(phi)
    
    return '\n\n'.join(parts)


# 对话历史优化配置

def clean_action_descriptions(text: str) -> str:
    """
    后处理：移除AI回复中的括号动作描述
    匹配中文括号（）和英文括号()中的内容
    """
    import re
    # 移除中文括号内容：（xxx）
    text = re.sub(r'（[^）]*）', '', text)
    # 移除英文括号内容：(xxx) 但保留 (笑)、(哭) 等纯表情短词（不超过4字）
    text = re.sub(r'\(([^)]{5,})\)', '', text)
    # 清理多余空格
    text = re.sub(r'\s{2,}', ' ', text).strip()
    return text


MAX_HISTORY_MESSAGES = 20      # 最多保留的对话轮数
MAX_HISTORY_TOKENS = 3000      # 对话历史的token预算
TOKENS_PER_MESSAGE = 4         # 每条消息的固定开销


def estimate_tokens(text: str) -> int:
    """粗略估算token数（中文约1字=1token，英文约4字符=1token）"""
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return chinese_chars + other_chars // 4


def get_optimized_history(
    conversation_history: Optional[List[dict]],
    max_messages: int = MAX_HISTORY_MESSAGES,
    max_tokens: int = MAX_HISTORY_TOKENS
) -> List[dict]:
    """
    优化对话历史：
    1. 限制消息数量
    2. 限制token总数
    3. 优先保留最近的对话
    """
    if not conversation_history:
        return []
    
    # 第一步：按消息数量截断，保留最近的
    trimmed = conversation_history[-max_messages:] if len(conversation_history) > max_messages else conversation_history
    
    # 第二步：按token预算截断
    selected = []
    total_tokens = 0
    
    # 从后往前遍历，优先保留最近的对话
    for msg in reversed(trimmed):
        content = msg.get('content', '')
        msg_tokens = estimate_tokens(content) + TOKENS_PER_MESSAGE
        
        # 单条消息就超预算，截断内容
        if msg_tokens > max_tokens // 2:
            content = content[:200] + "...（内容过长已截断）"
            msg_tokens = estimate_tokens(content) + TOKENS_PER_MESSAGE
        
        if total_tokens + msg_tokens > max_tokens:
            break
        
        selected.insert(0, {
            "role": msg.get('role', 'user'),
            "content": content
        })
        total_tokens += msg_tokens
    
    return selected


async def chat_with_ai(
    message: str,
    character: Character,
    user: User,
    db: Session,
    conversation_history: Optional[List[dict]] = None
) -> str:
    """与AI角色对话（优化版，支持自动摘要）"""
    
    # 优化对话历史
    optimized_history = get_optimized_history(conversation_history)
    
    # 构建聊天历史文本（用于世界书扫描）
    chat_text_history = []
    for msg in optimized_history:
        chat_text_history.append(msg.get('content', ''))
    chat_text_history.append(message)
    
    system_prompt = generate_character_prompt(
        character, user, db, chat_text_history
    )
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(optimized_history)
    messages.append({"role": "user", "content": message})
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {AI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": AI_MODEL,
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": 500
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                
                # 后处理：过滤括号动作描述
                ai_response = clean_action_descriptions(ai_response)
                
                # 异步触发摘要生成（不阻塞回复）
                # 构建完整的对话历史用于摘要
                full_history = list(conversation_history) if conversation_history else []
                full_history.append({"role": "user", "content": message})
                full_history.append({"role": "assistant", "content": ai_response})
                
                # 检查是否需要生成摘要
                try:
                    await maybe_summarize_conversation(
                        user.id, character.id, full_history, db
                    )
                except Exception as e:
                    # 摘要失败不影响正常对话
                    print(f"摘要生成失败: {e}")
                
                return ai_response
            else:
                return f"[{character.name}] 嗯...让我想想...（AI服务暂时不可用，请检查API配置）"
    
    except Exception as e:
        return f"[{character.name}] 啊，刚才有点走神了...（连接错误: {str(e)[:50]}）"


def update_intimacy(user: User, message_content: str, db: Session):
    """根据聊天内容更新亲密度"""
    increase = 0.5
    
    if len(message_content) > 20:
        increase += 0.3
    if len(message_content) > 50:
        increase += 0.2
    
    positive_words = ["喜欢", "爱", "谢谢", "开心", "想你", "好听", "棒", "厉害"]
    for word in positive_words:
        if word in message_content:
            increase += 0.5
            break
    
    user.intimacy = min(100.0, user.intimacy + increase)
    db.commit()


# ========== 对话摘要与长期记忆 ==========

SUMMARY_TRIGGER_MESSAGES = 20  # 达到多少条消息触发摘要
SUMMARY_BATCH_SIZE = 10        # 每次摘要处理的消息数量


async def generate_conversation_summary(
    messages: List[dict],
    character_name: str,
    username: str
) -> dict:
    """
    生成对话摘要
    返回: {"summary": "摘要内容", "key_topics": ["主题1", "主题2"]}
    """
    if not messages:
        return {"summary": "", "key_topics": []}
    
    # 构建对话文本
    dialogue_text = ""
    for msg in messages:
        role = "用户" if msg.get('role') == 'user' else character_name
        content = msg.get('content', '')[:200]  # 限制单条长度
        dialogue_text += f"{role}: {content}\n"
    
    summary_prompt = f"""请对以下对话生成简洁的摘要（100字以内），并提取关键主题。

对话双方: {username} 和 {character_name}

对话内容:
{dialogue_text}

请按以下格式回复:
摘要: [对话摘要，包含主要讨论内容、关系进展、重要事件]
主题: [主题1], [主题2], [主题3]
"""
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {AI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": AI_MODEL,
                    "messages": [{"role": "user", "content": summary_prompt}],
                    "temperature": 0.5,
                    "max_tokens": 300
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                summary_text = result["choices"][0]["message"]["content"]
                
                # 解析摘要和主题
                summary = ""
                key_topics = []
                
                for line in summary_text.split('\n'):
                    if line.startswith('摘要:') or line.startswith('摘要：'):
                        summary = line[3:].strip()
                    elif line.startswith('主题:') or line.startswith('主题：'):
                        topics = line[3:].strip()
                        key_topics = [t.strip() for t in topics.split(',') if t.strip()]
                
                # 如果没解析到，使用整段文本作为摘要
                if not summary:
                    summary = summary_text[:200]
                
                return {"summary": summary, "key_topics": key_topics}
    
    except Exception as e:
        print(f"生成摘要失败: {e}")
    
    # 失败时返回简单摘要
    return {
        "summary": f"{username}和{character_name}进行了对话",
        "key_topics": ["对话"]
    }


async def extract_key_memories(
    messages: List[dict],
    character_name: str,
    username: str
) -> List[dict]:
    """
    从对话中提取关键记忆
    返回: [{"type": "fact/preference/event/emotion", "content": "...", "importance": 7}]
    """
    if len(messages) < 2:
        return []
    
    # 构建对话文本（只取最近的几条）
    recent_messages = messages[-6:] if len(messages) > 6 else messages
    dialogue_text = ""
    for msg in recent_messages:
        role = "用户" if msg.get('role') == 'user' else character_name
        content = msg.get('content', '')
        dialogue_text += f"{role}: {content}\n"
    
    extract_prompt = f"""请从以下对话中提取关于用户({username})的关键信息。

对话内容:
{dialogue_text}

请提取以下类型的信息（每行一条，最多5条）:
- 事实: 用户提到的关于自己的客观信息（姓名、职业、爱好等）
- 偏好: 用户喜欢/不喜欢什么
- 事件: 用户提到的计划或发生的事情
- 情绪: 用户当前的情绪状态

格式示例:
[事实] 用户是一名程序员
[偏好] 用户喜欢听音乐
[事件] 用户明天要参加考试
[情绪] 用户感到开心

如果没有值得提取的信息，请回复"无"。"""
    
    memories = []
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {AI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": AI_MODEL,
                    "messages": [{"role": "user", "content": extract_prompt}],
                    "temperature": 0.3,
                    "max_tokens": 300
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                extract_text = result["choices"][0]["message"]["content"]
                
                # 解析提取的记忆
                type_map = {
                    "事实": "fact",
                    "偏好": "preference", 
                    "事件": "event",
                    "情绪": "emotion"
                }
                
                for line in extract_text.split('\n'):
                    line = line.strip()
                    if not line or line == "无":
                        continue
                    
                    # 匹配 [类型] 内容 格式
                    for cn_type, en_type in type_map.items():
                        if f"[{cn_type}]" in line or f"【{cn_type}】" in line:
                            content = line.split(']', 1)[-1].split('】', 1)[-1].strip()
                            if content and len(content) > 3:
                                # 根据类型设置重要性
                                importance = 7 if en_type == "preference" else 6
                                memories.append({
                                    "type": en_type,
                                    "content": content,
                                    "importance": importance
                                })
                            break
    
    except Exception as e:
        print(f"提取记忆失败: {e}")
    
    return memories


async def maybe_summarize_conversation(
    user_id: int,
    character_id: int,
    all_messages: List[dict],
    db: Session
) -> Optional[ConversationSummary]:
    """
    检查是否需要生成摘要，如果需要则生成并保存
    返回生成的摘要或None
    """
    # 获取已有的摘要数量
    existing_summaries = db.query(ConversationSummary).filter(
        ConversationSummary.user_id == user_id,
        ConversationSummary.character_id == character_id
    ).all()
    
    summarized_count = sum(s.message_count for s in existing_summaries)
    unsummarized_messages = all_messages[summarized_count:]
    
    # 检查是否达到触发条件
    if len(unsummarized_messages) < SUMMARY_TRIGGER_MESSAGES:
        return None
    
    # 取前SUMMARY_BATCH_SIZE条进行摘要
    messages_to_summarize = unsummarized_messages[:SUMMARY_BATCH_SIZE]
    
    # 获取角色和用户信息
    character = db.query(Character).filter(Character.id == character_id).first()
    user = db.query(User).filter(User.id == user_id).first()
    
    if not character or not user:
        return None
    
    # 生成摘要
    summary_result = await generate_conversation_summary(
        messages_to_summarize,
        character.name,
        user.username
    )
    
    # 计算时间范围
    start_time = datetime.now()
    end_time = datetime.now()
    
    # 保存摘要
    summary = ConversationSummary(
        user_id=user_id,
        character_id=character_id,
        summary=summary_result["summary"],
        key_topics=json.dumps(summary_result["key_topics"], ensure_ascii=False),
        message_count=len(messages_to_summarize),
        start_time=start_time,
        end_time=end_time
    )
    db.add(summary)
    
    # 提取关键记忆
    memories = await extract_key_memories(
        messages_to_summarize,
        character.name,
        user.username
    )
    
    for mem in memories:
        # 检查是否已有相似记忆
        existing = db.query(UserMemory).filter(
            UserMemory.user_id == user_id,
            UserMemory.character_id == character_id,
            UserMemory.memory_type == mem["type"],
            UserMemory.content == mem["content"]
        ).first()
        
        if not existing:
            user_memory = UserMemory(
                user_id=user_id,
                character_id=character_id,
                memory_type=mem["type"],
                content=mem["content"],
                importance=mem["importance"]
            )
            db.add(user_memory)
    
    db.commit()
    return summary


def get_summaries_for_context(
    user_id: int,
    character_id: int,
    db: Session,
    limit: int = 3
) -> str:
    """
    获取摘要作为上下文
    返回格式化的摘要文本
    """
    summaries = db.query(ConversationSummary).filter(
        ConversationSummary.user_id == user_id,
        ConversationSummary.character_id == character_id
    ).order_by(ConversationSummary.created_at.desc()).limit(limit).all()
    
    if not summaries:
        return ""
    
    context_parts = ["【之前的对话摘要】"]
    for i, s in enumerate(reversed(summaries), 1):
        context_parts.append(f"第{i}段: {s.summary}")
        
        # 添加关键主题
        if s.key_topics:
            try:
                topics = json.loads(s.key_topics)
                if topics:
                    context_parts.append(f"  主题: {', '.join(topics)}")
            except:
                pass
    
    return '\n'.join(context_parts)


def get_user_memories_for_context(
    user_id: int,
    character_id: int,
    db: Session,
    limit: int = 10
) -> str:
    """
    获取用户记忆作为上下文
    返回格式化的记忆文本
    """
    memories = db.query(UserMemory).filter(
        UserMemory.user_id == user_id,
        UserMemory.character_id == character_id,
        UserMemory.is_active == True
    ).order_by(UserMemory.importance.desc(), UserMemory.updated_at.desc()).limit(limit).all()
    
    if not memories:
        return ""
    
    type_labels = {
        "fact": "关于用户",
        "preference": "用户喜好",
        "event": "重要事件",
        "emotion": "情绪状态"
    }
    
    context_parts = ["【关于用户的重要信息】"]
    for m in memories:
        label = type_labels.get(m.memory_type, "信息")
        context_parts.append(f"- [{label}] {m.content}")
    
    return '\n'.join(context_parts)

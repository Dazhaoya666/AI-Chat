"""
傻酒馆（SillyTavern）角色卡和世界书导入/导出服务
支持 V1/V2 JSON 格式和 PNG 嵌入格式
"""
import json
import base64
import re
import struct
import zlib
from typing import Optional, Tuple
from database import Character, WorldBook, LoreEntry


# ========== PNG 元数据提取 ==========

def extract_png_text_chunk(png_bytes: bytes) -> Optional[str]:
    """从 PNG 文件中提取 tEXt 数据块中的角色卡 JSON"""
    # PNG 签名: 8 bytes
    if png_bytes[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    
    pos = 8
    while pos < len(png_bytes):
        # 读取数据块长度 (4 bytes big-endian)
        if pos + 8 > len(png_bytes):
            break
        chunk_len = struct.unpack('>I', png_bytes[pos:pos+4])[0]
        chunk_type = png_bytes[pos+4:pos+8]
        chunk_data = png_bytes[pos+8:pos+8+chunk_len]
        
        # 检查 tEXt 数据块
        if chunk_type == b'tEXt':
            # tEXt 格式: keyword\0text
            null_idx = chunk_data.find(b'\x00')
            if null_idx >= 0:
                keyword = chunk_data[:null_idx].decode('latin-1')
                text_data = chunk_data[null_idx+1:]
                
                # 傻酒馆角色卡使用 "chara" 关键字
                if keyword == 'chara':
                    try:
                        return base64.b64decode(text_data).decode('utf-8')
                    except Exception:
                        return text_data.decode('utf-8', errors='ignore')
        
        # 跳到下一个数据块 (length + 4 + type + 4 + data + crc)
        pos += 12 + chunk_len
    
    return None


# ========== 角色卡解析 ==========

def parse_character_card(file_content: str, filename: str = "") -> dict:
    """
    解析傻酒馆角色卡，支持:
    - V1 JSON (字段在根层级)
    - V2 JSON (spec="chara_card_v2", 字段在 data 下)
    - PNG 文件 (Base64 编码的 JSON 嵌入在 tEXt 数据块)
    
    返回标准化的角色数据字典
    """
    # 如果是 PNG 文件，先提取嵌入的 JSON
    if filename.lower().endswith('.png'):
        try:
            png_bytes = base64.b64decode(file_content) if not file_content.startswith(b'\x89PNG') else file_content
            if isinstance(file_content, str):
                png_bytes = base64.b64decode(file_content)
            json_str = extract_png_text_chunk(png_bytes)
            if json_str:
                file_content = json_str
            else:
                raise ValueError("PNG 文件中未找到角色卡数据")
        except Exception as e:
            raise ValueError(f"PNG 解析失败: {str(e)}")
    
    # 解析 JSON
    try:
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8')
        card_data = json.loads(file_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {str(e)}")
    
    # 判断 V1 还是 V2
    if card_data.get('spec') == 'chara_card_v2':
        return _parse_v2_card(card_data)
    else:
        return _parse_v1_card(card_data)


def _parse_v1_card(data: dict) -> dict:
    """解析 V1 角色卡"""
    return {
        'name': data.get('name', '未命名角色'),
        'description': data.get('description', ''),
        'personality': data.get('personality', ''),
        'scenario': data.get('scenario', ''),
        'first_mes': data.get('first_mes', ''),
        'mes_example': data.get('mes_example', ''),
        'system_prompt': data.get('system_prompt', ''),
        'post_history_instructions': data.get('post_history_instructions', ''),
        'creator_notes': data.get('creator_notes', ''),
        'creator': data.get('creator', ''),
        'character_version': data.get('character_version', '1.0.0'),
        'tags': ','.join(data.get('tags', [])) if isinstance(data.get('tags'), list) else data.get('tags', ''),
        'alternate_greetings': json.dumps(data.get('alternate_greetings', []), ensure_ascii=False),
        # 兼容旧字段映射
        'background': data.get('description', ''),
        'habits': data.get('personality', ''),
        'world_view': data.get('scenario', ''),
    }


def _parse_v2_card(data: dict) -> dict:
    """解析 V2 角色卡"""
    d = data.get('data', data)
    
    # 处理内嵌的角色书 (character_book)
    character_book = d.get('character_book')
    
    return {
        'name': d.get('name', '未命名角色'),
        'description': d.get('description', ''),
        'personality': d.get('personality', ''),
        'scenario': d.get('scenario', ''),
        'first_mes': d.get('first_mes', ''),
        'mes_example': d.get('mes_example', ''),
        'system_prompt': d.get('system_prompt', ''),
        'post_history_instructions': d.get('post_history_instructions', ''),
        'creator_notes': d.get('creator_notes', ''),
        'creator': d.get('creator', ''),
        'character_version': d.get('character_version', '2.0.0'),
        'tags': ','.join(d.get('tags', [])) if isinstance(d.get('tags'), list) else d.get('tags', ''),
        'alternate_greetings': json.dumps(d.get('alternate_greetings', []), ensure_ascii=False),
        # 兼容旧字段映射
        'background': d.get('description', ''),
        'habits': d.get('personality', ''),
        'world_view': d.get('scenario', ''),
        # 内嵌角色书数据（后续处理）
        '_character_book': character_book,
    }


# ========== 角色卡导出 ==========

def export_character_card(character: Character, include_worldbook: bool = False) -> dict:
    """导出为傻酒馆 V2 角色卡格式"""
    tags_list = [t.strip() for t in character.tags.split(',') if t.strip()] if character.tags else []
    
    alt_greetings = []
    if character.alternate_greetings:
        try:
            alt_greetings = json.loads(character.alternate_greetings)
        except:
            alt_greetings = []
    
    card = {
        'spec': 'chara_card_v2',
        'spec_version': '2.0',
        'data': {
            'name': character.name,
            'description': character.description or character.background,
            'personality': character.personality or character.habits,
            'scenario': character.scenario or character.world_view,
            'first_mes': character.first_mes,
            'mes_example': character.mes_example,
            'system_prompt': character.system_prompt,
            'post_history_instructions': character.post_history_instructions,
            'creator_notes': character.creator_notes,
            'creator': character.creator,
            'character_version': character.character_version,
            'tags': tags_list,
            'alternate_greetings': alt_greetings,
            'extensions': {},
        }
    }
    
    return card


# ========== 世界书解析 ==========

def parse_world_book(file_content: str, filename: str = "") -> dict:
    """
    解析傻酒馆世界书 JSON
    支持两种格式:
    1. V2 规范: entries 是数组
    2. SillyTavern 实际格式: entries 是对象（数字字符串为键）
    """
    try:
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8')
        data = json.loads(file_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"世界书 JSON 解析失败: {str(e)}")
    
    worldbook = {
        'name': data.get('name', '未命名世界书'),
        'description': data.get('description', ''),
        'scan_depth': data.get('scan_depth', 50) or 50,
        'token_budget': data.get('token_budget', 2048) or 2048,
        'recursive_scanning': data.get('recursive_scanning', True),
        'entries': [],
    }
    
    raw_entries = data.get('entries', {})
    
    # entries 可能是数组或对象
    if isinstance(raw_entries, list):
        entries_list = raw_entries
    elif isinstance(raw_entries, dict):
        entries_list = list(raw_entries.values())
    else:
        entries_list = []
    
    for entry in entries_list:
        parsed = _parse_lore_entry(entry)
        if parsed:
            worldbook['entries'].append(parsed)
    
    return worldbook


def _parse_lore_entry(entry: dict) -> Optional[dict]:
    """解析单条世界书条目，兼容多种字段命名"""
    if not entry:
        return None
    
    # 关键词字段兼容: keys / key
    keys = entry.get('keys', entry.get('key', []))
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split(',') if k.strip()]
    elif not isinstance(keys, list):
        keys = []
    
    # 次要关键词兼容: secondary_keys / keysecondary
    secondary_keys = entry.get('secondary_keys', entry.get('keysecondary', []))
    if isinstance(secondary_keys, str):
        secondary_keys = [k.strip() for k in secondary_keys.split(',') if k.strip()]
    elif not isinstance(secondary_keys, list):
        secondary_keys = []
    
    return {
        'keys': ','.join(keys),
        'secondary_keys': ','.join(secondary_keys),
        'content': entry.get('content', ''),
        'comment': entry.get('comment', ''),
        'name': entry.get('name', entry.get('comment', '')),
        'enabled': entry.get('enabled', True),
        'constant': entry.get('constant', False),
        'selective': entry.get('selective', False),
        'case_sensitive': entry.get('case_sensitive', False),
        'use_regex': entry.get('use_regex', False),
        'insertion_order': entry.get('insertion_order', entry.get('order', 100)),
        'priority': entry.get('priority', 10),
        'position': entry.get('position', 'before_char'),
        'scan_depth': entry.get('scan_depth', 0) or 0,
        'probability': entry.get('probability', 100) or 100,
        'sticky': entry.get('sticky', 0) or 0,
        'cooldown': entry.get('cooldown', 0) or 0,
        'delay': entry.get('delay', 0) or 0,
    }


# ========== 世界书导出 ==========

def export_world_book(worldbook: WorldBook) -> dict:
    """导出为傻酒馆世界书 JSON 格式"""
    entries_obj = {}
    for i, entry in enumerate(worldbook.entries):
        keys = [k.strip() for k in entry.keys.split(',') if k.strip()]
        secondary_keys = [k.strip() for k in entry.secondary_keys.split(',') if k.strip()]
        
        entries_obj[str(i)] = {
            'key': keys,
            'keysecondary': secondary_keys,
            'comment': entry.comment,
            'content': entry.content,
            'constant': entry.constant,
            'selective': entry.selective,
            'insertion_order': entry.insertion_order,
            'enabled': entry.enabled,
            'position': entry.position,
            'case_sensitive': entry.case_sensitive,
            'name': entry.name,
            'priority': entry.priority,
            'id': i,
            'use_regex': entry.use_regex,
            'scan_depth': entry.scan_depth,
            'probability': entry.probability,
            'sticky': entry.sticky,
            'cooldown': entry.cooldown,
            'delay': entry.delay,
            'extensions': {},
        }
    
    return {
        'name': worldbook.name,
        'description': worldbook.description,
        'scan_depth': worldbook.scan_depth,
        'token_budget': worldbook.token_budget,
        'recursive_scanning': worldbook.recursive_scanning,
        'entries': entries_obj,
        'extensions': {},
    }

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()
engine = create_engine("sqlite:///./ai_chat.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    intimacy = Column(Float, default=0.0)
    # 用户状态: active(正常), temp_banned(临时封禁), banned(永久封禁)
    status = Column(String, default="active")
    ban_until = Column(DateTime, nullable=True)  # 临时封禁到期时间
    ban_reason = Column(Text, default="")  # 封禁原因
    
    messages = relationship("Message", back_populates="user")
    moments_likes = relationship("MomentLike", back_populates="user")

class Character(Base):
    __tablename__ = "characters"
    
    id = Column(Integer, primary_key=True, index=True)
    # === 傻酒馆角色卡字段 ===
    name = Column(String, index=True)
    description = Column(Text, default="")
    personality = Column(Text, default="")
    scenario = Column(Text, default="")
    first_mes = Column(Text, default="")
    mes_example = Column(Text, default="")
    system_prompt = Column(Text, default="")
    post_history_instructions = Column(Text, default="")
    creator_notes = Column(Text, default="")
    creator = Column(String, default="")
    character_version = Column(String, default="1.0.0")
    tags = Column(Text, default="")
    alternate_greetings = Column(Text, default="")
    # === 兼容旧字段 ===
    background = Column(Text, default="")
    habits = Column(Text, default="")
    world_view = Column(Text, default="")
    # === 系统字段 ===
    avatar = Column(String, default="")  # 角色头像路径
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    
    experiences = relationship("Experience", back_populates="character")
    messages = relationship("Message", back_populates="character")
    moments = relationship("CharacterMoment", back_populates="character")

class Experience(Base):
    __tablename__ = "experiences"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"))
    date = Column(DateTime, default=datetime.now)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    character = relationship("Character", back_populates="experiences")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    character_id = Column(Integer, ForeignKey("characters.id"))
    content = Column(Text)
    is_user = Column(Boolean)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="messages")
    character = relationship("Character", back_populates="messages")

# ========== 朋友圈 / 角色动态 ==========

class CharacterMoment(Base):
    __tablename__ = "character_moments"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"))
    content = Column(Text)  # 文字内容
    images = Column(Text, default="")  # JSON数组存储图片URL列表
    created_at = Column(DateTime, default=datetime.now)
    likes_count = Column(Integer, default=0)
    
    character = relationship("Character", back_populates="moments")
    likes = relationship("MomentLike", back_populates="moment", cascade="all, delete-orphan")

class MomentLike(Base):
    __tablename__ = "moment_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    moment_id = Column(Integer, ForeignKey("character_moments.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)
    
    moment = relationship("CharacterMoment", back_populates="likes")
    user = relationship("User", back_populates="moments_likes")

# ========== 世界书 / Lorebook ==========

class WorldBook(Base):
    __tablename__ = "worldbooks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, default="")
    scan_depth = Column(Integer, default=50)
    token_budget = Column(Integer, default=2048)
    recursive_scanning = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    entries = relationship("LoreEntry", back_populates="worldbook", cascade="all, delete-orphan")

class LoreEntry(Base):
    __tablename__ = "lore_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    worldbook_id = Column(Integer, ForeignKey("worldbooks.id"))
    keys = Column(Text, default="")
    secondary_keys = Column(Text, default="")
    content = Column(Text, default="")
    comment = Column(Text, default="")
    name = Column(String, default="")
    enabled = Column(Boolean, default=True)
    constant = Column(Boolean, default=False)
    selective = Column(Boolean, default=False)
    case_sensitive = Column(Boolean, default=False)
    use_regex = Column(Boolean, default=False)
    insertion_order = Column(Integer, default=100)
    priority = Column(Integer, default=10)
    position = Column(String, default="before_char")
    scan_depth = Column(Integer, default=0)
    probability = Column(Integer, default=100)
    sticky = Column(Integer, default=0)
    cooldown = Column(Integer, default=0)
    delay = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    
    worldbook = relationship("WorldBook", back_populates="entries")

class CharacterWorldBook(Base):
    __tablename__ = "character_worldbooks"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"))
    worldbook_id = Column(Integer, ForeignKey("worldbooks.id"))
    created_at = Column(DateTime, default=datetime.now)


# ========== 对话摘要 / 长期记忆 ==========

class ConversationSummary(Base):
    """对话摘要 - 存储压缩后的对话历史"""
    __tablename__ = "conversation_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)
    summary = Column(Text)  # 摘要内容
    key_topics = Column(Text, default="")  # 关键主题（JSON数组）
    message_count = Column(Integer, default=0)  # 涵盖的消息数量
    start_time = Column(DateTime)  # 摘要涵盖的起始时间
    end_time = Column(DateTime)  # 摘要涵盖的结束时间
    created_at = Column(DateTime, default=datetime.now)


class UserMemory(Base):
    """用户记忆 - 存储关于用户的关键信息"""
    __tablename__ = "user_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)
    memory_type = Column(String, default="fact")  # fact(事实), preference(偏好), event(事件), emotion(情绪)
    content = Column(Text)  # 记忆内容
    importance = Column(Integer, default=5)  # 重要性 1-10
    source_message_id = Column(Integer, nullable=True)  # 来源消息ID
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)  # 是否有效（可被更新或删除）


def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone, timedelta

BJ_TZ = timezone(timedelta(hours=8))

def now():
    return datetime.now(BJ_TZ)

Base = declarative_base()
engine = create_engine("sqlite:///./ai_chat.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=now)
    intimacy = Column(Float, default=0.0)
    age = Column(Integer, nullable=True)
    gender = Column(String, default="")
    status = Column(String, default="active")
    ban_until = Column(DateTime, nullable=True)
    ban_reason = Column(Text, default="")
    
    messages = relationship("Message", back_populates="user")
    moments_likes = relationship("MomentLike", back_populates="user")

class Character(Base):
    __tablename__ = "characters"
    
    id = Column(Integer, primary_key=True, index=True)
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
    background = Column(Text, default="")
    habits = Column(Text, default="")
    world_view = Column(Text, default="")
    avatar = Column(String, default="")
    created_at = Column(DateTime, default=now)
    is_active = Column(Boolean, default=True)
    
    experiences = relationship("Experience", back_populates="character")
    messages = relationship("Message", back_populates="character")
    moments = relationship("CharacterMoment", back_populates="character")

class Experience(Base):
    __tablename__ = "experiences"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"))
    date = Column(DateTime, default=now)
    content = Column(Text)
    created_at = Column(DateTime, default=now)
    
    character = relationship("Character", back_populates="experiences")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    character_id = Column(Integer, ForeignKey("characters.id"))
    content = Column(Text)
    is_user = Column(Boolean)
    created_at = Column(DateTime, default=now)
    
    user = relationship("User", back_populates="messages")
    character = relationship("Character", back_populates="messages")

class CharacterMoment(Base):
    __tablename__ = "character_moments"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"))
    content = Column(Text)
    images = Column(Text, default="")
    created_at = Column(DateTime, default=now)
    likes_count = Column(Integer, default=0)
    
    character = relationship("Character", back_populates="moments")
    likes = relationship("MomentLike", back_populates="moment", cascade="all, delete-orphan")

class MomentLike(Base):
    __tablename__ = "moment_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    moment_id = Column(Integer, ForeignKey("character_moments.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now)
    
    moment = relationship("CharacterMoment", back_populates="likes")
    user = relationship("User", back_populates="moments_likes")

class WorldBook(Base):
    __tablename__ = "worldbooks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, default="")
    scan_depth = Column(Integer, default=50)
    token_budget = Column(Integer, default=2048)
    recursive_scanning = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)
    
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
    created_at = Column(DateTime, default=now)
    
    worldbook = relationship("WorldBook", back_populates="entries")

class CharacterWorldBook(Base):
    __tablename__ = "character_worldbooks"
    
    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"))
    worldbook_id = Column(Integer, ForeignKey("worldbooks.id"))
    created_at = Column(DateTime, default=now)


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)
    summary = Column(Text)
    key_topics = Column(Text, default="")
    message_count = Column(Integer, default=0)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    created_at = Column(DateTime, default=now)


class UserMemory(Base):
    __tablename__ = "user_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True)
    memory_type = Column(String, default="fact")
    content = Column(Text)
    importance = Column(Integer, default=5)
    source_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now)
    is_active = Column(Boolean, default=True)


def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

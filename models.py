from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ========== 用户相关 ==========
class UserCreate(BaseModel):
    username: str
    password: str
    age: Optional[int] = None
    gender: Optional[str] = ""

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    age: Optional[int] = None
    gender: str
    created_at: datetime
    class Config:
        from_attributes = True

class UserAdminResponse(BaseModel):
    id: int
    username: str
    hashed_password: str
    age: Optional[int] = None
    gender: str
    intimacy: float
    status: str
    ban_until: Optional[datetime]
    ban_reason: str
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# ========== 角色相关 ==========
class CharacterCreate(BaseModel):
    name: str
    avatar: str = ""
    description: str = ""
    personality: str = ""
    scenario: str = ""
    first_mes: str = ""
    mes_example: str = ""
    system_prompt: str = ""
    post_history_instructions: str = ""
    creator_notes: str = ""
    creator: str = ""
    character_version: str = "1.0.0"
    tags: str = ""
    alternate_greetings: str = ""
    background: str = ""
    habits: str = ""
    world_view: str = ""
    is_active: bool = True

class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    personality: Optional[str] = None
    scenario: Optional[str] = None
    first_mes: Optional[str] = None
    mes_example: Optional[str] = None
    system_prompt: Optional[str] = None
    post_history_instructions: Optional[str] = None
    creator_notes: Optional[str] = None
    creator: Optional[str] = None
    character_version: Optional[str] = None
    tags: Optional[str] = None
    alternate_greetings: Optional[str] = None
    background: Optional[str] = None
    habits: Optional[str] = None
    world_view: Optional[str] = None
    is_active: Optional[bool] = None

class CharacterResponse(BaseModel):
    id: int
    name: str
    avatar: str = ""
    created_at: datetime
    is_active: bool
    class Config:
        from_attributes = True

class CharacterDetailResponse(BaseModel):
    """管理员看到的完整角色信息"""
    id: int
    name: str
    avatar: str = ""
    description: str
    personality: str
    scenario: str
    first_mes: str
    mes_example: str
    system_prompt: str
    post_history_instructions: str
    creator_notes: str
    creator: str
    character_version: str
    tags: str
    alternate_greetings: str
    background: str
    habits: str
    world_view: str
    created_at: datetime
    is_active: bool
    class Config:
        from_attributes = True

# ========== 经历相关 ==========
class ExperienceCreate(BaseModel):
    character_id: int
    content: str
    date: Optional[datetime] = None

class ExperienceResponse(BaseModel):
    id: int
    character_id: int
    date: datetime
    content: str
    created_at: datetime
    class Config:
        from_attributes = True

# ========== 朋友圈相关 ==========
class MomentCreate(BaseModel):
    character_id: int
    content: str
    images: str = ""  # JSON数组

class MomentResponse(BaseModel):
    id: int
    character_id: int
    character_name: str
    content: str
    images: str
    created_at: datetime
    likes_count: int
    is_liked: bool = False
    class Config:
        from_attributes = True

class MomentLikeCreate(BaseModel):
    moment_id: int

# ========== 世界书相关 ==========
class LoreEntryCreate(BaseModel):
    keys: str = ""
    secondary_keys: str = ""
    content: str = ""
    comment: str = ""
    name: str = ""
    enabled: bool = True
    constant: bool = False
    selective: bool = False
    case_sensitive: bool = False
    use_regex: bool = False
    insertion_order: int = 100
    priority: int = 10
    position: str = "before_char"
    scan_depth: int = 0
    probability: int = 100
    sticky: int = 0
    cooldown: int = 0
    delay: int = 0

class LoreEntryUpdate(BaseModel):
    keys: Optional[str] = None
    secondary_keys: Optional[str] = None
    content: Optional[str] = None
    comment: Optional[str] = None
    name: Optional[str] = None
    enabled: Optional[bool] = None
    constant: Optional[bool] = None
    selective: Optional[bool] = None
    case_sensitive: Optional[bool] = None
    use_regex: Optional[bool] = None
    insertion_order: Optional[int] = None
    priority: Optional[int] = None
    position: Optional[str] = None
    scan_depth: Optional[int] = None
    probability: Optional[int] = None
    sticky: Optional[int] = None
    cooldown: Optional[int] = None
    delay: Optional[int] = None

class LoreEntryResponse(BaseModel):
    id: int
    worldbook_id: int
    keys: str
    secondary_keys: str
    content: str
    comment: str
    name: str
    enabled: bool
    constant: bool
    selective: bool
    case_sensitive: bool
    use_regex: bool
    insertion_order: int
    priority: int
    position: str
    scan_depth: int
    probability: int
    sticky: int
    cooldown: int
    delay: int
    created_at: datetime
    class Config:
        from_attributes = True

class WorldBookCreate(BaseModel):
    name: str
    description: str = ""
    scan_depth: int = 50
    token_budget: int = 2048
    recursive_scanning: bool = True

class WorldBookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scan_depth: Optional[int] = None
    token_budget: Optional[int] = None
    recursive_scanning: Optional[bool] = None

class WorldBookResponse(BaseModel):
    id: int
    name: str
    description: str
    scan_depth: int
    token_budget: int
    recursive_scanning: bool
    created_at: datetime
    entry_count: int = 0
    class Config:
        from_attributes = True

# ========== 消息相关 ==========
class MessageResponse(BaseModel):
    id: int
    content: str
    is_user: bool
    created_at: datetime
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    character_id: Optional[int] = None

# ========== 管理员操作 ==========
class UserStatusUpdate(BaseModel):
    status: str
    ban_until: Optional[datetime] = None
    ban_reason: str = ""

class UserIntimacyUpdate(BaseModel):
    intimacy: float

class UserUpdate(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None

from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

from database import (
    init_db, get_db, User, Character, Experience, Message,
    WorldBook, LoreEntry, CharacterWorldBook,
    CharacterMoment, MomentLike
)
from models import (
    UserCreate, UserLogin, UserResponse, UserAdminResponse,
    UserStatusUpdate, UserIntimacyUpdate,
    Token, CharacterCreate, CharacterUpdate, CharacterResponse, CharacterDetailResponse,
    ExperienceCreate, ExperienceResponse,
    MomentCreate, MomentResponse, MomentLikeCreate,
    WorldBookCreate, WorldBookUpdate, WorldBookResponse,
    LoreEntryCreate, LoreEntryUpdate, LoreEntryResponse,
    MessageResponse, ChatRequest
)
from auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, get_current_admin
)
from ai_service import chat_with_ai, update_intimacy
from card_service import parse_character_card, export_character_card, parse_world_book, export_world_book

app = FastAPI(title="AI Chat Application", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
except:
    pass
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.on_event("startup")
async def startup():
    init_db()

# ========== 页面路由 ==========

@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/chat")
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/moments")
async def moments_page(request: Request):
    return templates.TemplateResponse("moments.html", {"request": request})

# 管理员独立登录页面
@app.get("/admin/login")
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.get("/admin")
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

# ========== 用户认证 API ==========

@app.post("/api/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/login", response_model=Token)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if db_user.username == "admin":
        raise HTTPException(status_code=403, detail="Please use admin login page")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ========== 管理员认证 API ==========

@app.post("/api/admin/login", response_model=Token)
async def admin_login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if db_user.username != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# ========== 角色管理 API（用户可见） ==========

@app.get("/api/characters/active", response_model=List[CharacterResponse])
async def list_active_characters(db: Session = Depends(get_db)):
    """用户只能看到角色的基本信息"""
    chars = db.query(Character).filter(Character.is_active == True).all()
    return chars

# ========== 角色管理 API（管理员） ==========

@app.get("/api/characters", response_model=List[CharacterDetailResponse])
async def list_all_characters(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return db.query(Character).all()

@app.get("/api/characters/{character_id}", response_model=CharacterDetailResponse)
async def get_character_detail(character_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    char = db.query(Character).filter(Character.id == character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char

@app.post("/api/characters", response_model=CharacterDetailResponse)
async def create_character(character: CharacterCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    db_char = Character(**character.dict())
    db.add(db_char)
    db.commit()
    db.refresh(db_char)
    return db_char

@app.put("/api/characters/{character_id}", response_model=CharacterDetailResponse)
async def update_character(character_id: int, character: CharacterUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    db_char = db.query(Character).filter(Character.id == character_id).first()
    if not db_char:
        raise HTTPException(status_code=404, detail="Character not found")
    for key, value in character.dict(exclude_unset=True).items():
        setattr(db_char, key, value)
    db.commit()
    db.refresh(db_char)
    return db_char

@app.post("/api/characters/{character_id}/avatar")
async def upload_character_avatar(
    character_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """上传角色头像"""
    db_char = db.query(Character).filter(Character.id == character_id).first()
    if not db_char:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # 验证文件类型
    if file.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/GIF/WebP 图片")
    
    # 生成唯一文件名
    ext = file.filename.split('.')[-1] if file.filename and '.' in file.filename else 'jpg'
    filename = f"avatar_{character_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = UPLOAD_DIR / filename
    
    # 保存文件
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    # 删除旧头像
    if db_char.avatar:
        old_path = BASE_DIR / db_char.avatar.lstrip('/')
        if old_path.exists():
            old_path.unlink()
    
    # 更新数据库
    db_char.avatar = f"/static/uploads/{filename}"
    db.commit()
    db.refresh(db_char)
    
    return {"avatar": db_char.avatar}

@app.delete("/api/characters/{character_id}")
async def delete_character(character_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    db_char = db.query(Character).filter(Character.id == character_id).first()
    if not db_char:
        raise HTTPException(status_code=404, detail="Character not found")
    db.delete(db_char)
    db.commit()
    return {"message": "Character deleted"}

# 角色卡导入/导出
@app.post("/api/characters/import")
async def import_character(file: UploadFile = File(...), db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    try:
        content = await file.read()
        card_data = parse_character_card(content, file.filename or "")
        character_book = card_data.pop('_character_book', None)
        
        db_char = Character(**card_data)
        db.add(db_char)
        db.commit()
        db.refresh(db_char)
        
        if character_book and character_book.get('entries'):
            wb = WorldBook(
                name=f"{db_char.name}的专属知识库",
                description=character_book.get('description', ''),
                scan_depth=character_book.get('scan_depth', 50) or 50,
                token_budget=character_book.get('token_budget', 2048) or 2048,
                recursive_scanning=character_book.get('recursive_scanning', True),
            )
            db.add(wb)
            db.commit()
            db.refresh(wb)
            
            for entry_data in character_book['entries']:
                entry = LoreEntry(worldbook_id=wb.id, **entry_data)
                db.add(entry)
            db.commit()
            
            binding = CharacterWorldBook(character_id=db_char.id, worldbook_id=wb.id)
            db.add(binding)
            db.commit()
        
        return {"message": f"角色 '{db_char.name}' 导入成功", "character_id": db_char.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

@app.get("/api/characters/{character_id}/export")
async def export_character(character_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    char = db.query(Character).filter(Character.id == character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    card = export_character_card(char)
    return JSONResponse(content=card)

# ========== 经历管理 API（管理员） ==========

@app.get("/api/characters/{character_id}/experiences", response_model=List[ExperienceResponse])
async def list_experiences(character_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return db.query(Experience).filter(Experience.character_id == character_id).order_by(Experience.date.desc()).all()

@app.post("/api/experiences", response_model=ExperienceResponse)
async def create_experience(exp: ExperienceCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    char = db.query(Character).filter(Character.id == exp.character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    db_exp = Experience(**exp.dict())
    db.add(db_exp)
    db.commit()
    db.refresh(db_exp)
    return db_exp

@app.delete("/api/experiences/{experience_id}")
async def delete_experience(experience_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    exp = db.query(Experience).filter(Experience.id == experience_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")
    db.delete(exp)
    db.commit()
    return {"message": "Experience deleted"}

# ========== 朋友圈 API ==========

@app.get("/api/moments", response_model=List[MomentResponse])
async def list_moments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取所有角色的朋友圈动态"""
    moments = db.query(CharacterMoment).order_by(CharacterMoment.created_at.desc()).all()
    result = []
    for m in moments:
        is_liked = db.query(MomentLike).filter(
            MomentLike.moment_id == m.id,
            MomentLike.user_id == current_user.id
        ).first() is not None
        result.append(MomentResponse(
            id=m.id,
            character_id=m.character_id,
            character_name=m.character.name,
            content=m.content,
            images=m.images,
            created_at=m.created_at,
            likes_count=m.likes_count,
            is_liked=is_liked
        ))
    return result

@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...), admin: User = Depends(get_current_admin)):
    """上传图片"""
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/GIF/WEBP 格式")
    
    ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'jpg'
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = UPLOAD_DIR / filename
    
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    return {"url": f"/static/uploads/{filename}"}

@app.post("/api/moments")
async def create_moment(
    request: Request,
    character_id: int = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员发布朋友圈动态（支持图片上传）"""
    char = db.query(Character).filter(Character.id == character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # 手动从form中提取所有images文件（兼容单文件和多文件）
    form = await request.form()
    image_files = form.getlist("images")
    
    # 保存上传的图片
    image_urls = []
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    for img_file in image_files:
        if img_file and hasattr(img_file, 'content_type') and img_file.content_type in allowed_types:
            ext = img_file.filename.rsplit('.', 1)[-1] if '.' in img_file.filename else 'jpg'
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = UPLOAD_DIR / filename
            img_content = await img_file.read()
            with open(filepath, "wb") as f:
                f.write(img_content)
            image_urls.append(f"/static/uploads/{filename}")
    
    db_moment = CharacterMoment(
        character_id=character_id,
        content=content,
        images=json.dumps(image_urls, ensure_ascii=False) if image_urls else ""
    )
    db.add(db_moment)
    db.commit()
    db.refresh(db_moment)
    return MomentResponse(
        id=db_moment.id,
        character_id=db_moment.character_id,
        character_name=char.name,
        content=db_moment.content,
        images=db_moment.images,
        created_at=db_moment.created_at,
        likes_count=0,
        is_liked=False
    )

@app.post("/api/moments/{moment_id}/like")
async def like_moment(moment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """点赞/取消点赞"""
    moment = db.query(CharacterMoment).filter(CharacterMoment.id == moment_id).first()
    if not moment:
        raise HTTPException(status_code=404, detail="Moment not found")
    
    existing_like = db.query(MomentLike).filter(
        MomentLike.moment_id == moment_id,
        MomentLike.user_id == current_user.id
    ).first()
    
    if existing_like:
        # 取消点赞
        db.delete(existing_like)
        moment.likes_count = max(0, moment.likes_count - 1)
        db.commit()
        return {"message": "Unliked", "likes_count": moment.likes_count}
    else:
        # 点赞
        like = MomentLike(moment_id=moment_id, user_id=current_user.id)
        db.add(like)
        moment.likes_count += 1
        db.commit()
        return {"message": "Liked", "likes_count": moment.likes_count}

@app.delete("/api/moments/{moment_id}")
async def delete_moment(moment_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    moment = db.query(CharacterMoment).filter(CharacterMoment.id == moment_id).first()
    if not moment:
        raise HTTPException(status_code=404, detail="Moment not found")
    db.delete(moment)
    db.commit()
    return {"message": "Moment deleted"}

# ========== 世界书管理 API ==========

@app.get("/api/worldbooks", response_model=List[WorldBookResponse])
async def list_worldbooks(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    wbs = db.query(WorldBook).all()
    result = []
    for wb in wbs:
        resp = WorldBookResponse.model_validate(wb)
        resp.entry_count = len(wb.entries)
        result.append(resp)
    return result

@app.post("/api/worldbooks", response_model=WorldBookResponse)
async def create_worldbook(wb: WorldBookCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    db_wb = WorldBook(**wb.dict())
    db.add(db_wb)
    db.commit()
    db.refresh(db_wb)
    return WorldBookResponse.model_validate(db_wb)

@app.put("/api/worldbooks/{worldbook_id}", response_model=WorldBookResponse)
async def update_worldbook(worldbook_id: int, wb: WorldBookUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    db_wb = db.query(WorldBook).filter(WorldBook.id == worldbook_id).first()
    if not db_wb:
        raise HTTPException(status_code=404, detail="WorldBook not found")
    for key, value in wb.dict(exclude_unset=True).items():
        setattr(db_wb, key, value)
    db.commit()
    db.refresh(db_wb)
    resp = WorldBookResponse.model_validate(db_wb)
    resp.entry_count = len(db_wb.entries)
    return resp

@app.delete("/api/worldbooks/{worldbook_id}")
async def delete_worldbook(worldbook_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    wb = db.query(WorldBook).filter(WorldBook.id == worldbook_id).first()
    if not wb:
        raise HTTPException(status_code=404, detail="WorldBook not found")
    db.query(CharacterWorldBook).filter(CharacterWorldBook.worldbook_id == worldbook_id).delete()
    db.delete(wb)
    db.commit()
    return {"message": "WorldBook deleted"}

@app.post("/api/worldbooks/import")
async def import_worldbook(file: UploadFile = File(...), db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    try:
        content = await file.read()
        wb_data = parse_world_book(content, file.filename or "")
        
        wb = WorldBook(
            name=wb_data['name'],
            description=wb_data['description'],
            scan_depth=wb_data['scan_depth'],
            token_budget=wb_data['token_budget'],
            recursive_scanning=wb_data['recursive_scanning'],
        )
        db.add(wb)
        db.commit()
        db.refresh(wb)
        
        for entry_data in wb_data['entries']:
            entry = LoreEntry(worldbook_id=wb.id, **entry_data)
            db.add(entry)
        db.commit()
        
        return {"message": f"世界书 '{wb.name}' 导入成功", "worldbook_id": wb.id, "entry_count": len(wb_data['entries'])}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")

@app.get("/api/worldbooks/{worldbook_id}/export")
async def export_worldbook(worldbook_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    wb = db.query(WorldBook).filter(WorldBook.id == worldbook_id).first()
    if not wb:
        raise HTTPException(status_code=404, detail="WorldBook not found")
    return JSONResponse(content=export_world_book(wb))

@app.get("/api/worldbooks/{worldbook_id}/entries", response_model=List[LoreEntryResponse])
async def list_lore_entries(worldbook_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return db.query(LoreEntry).filter(LoreEntry.worldbook_id == worldbook_id).order_by(LoreEntry.insertion_order).all()

@app.post("/api/worldbooks/{worldbook_id}/entries", response_model=LoreEntryResponse)
async def create_lore_entry(worldbook_id: int, entry: LoreEntryCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    wb = db.query(WorldBook).filter(WorldBook.id == worldbook_id).first()
    if not wb:
        raise HTTPException(status_code=404, detail="WorldBook not found")
    db_entry = LoreEntry(worldbook_id=worldbook_id, **entry.dict())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

@app.put("/api/lore-entries/{entry_id}", response_model=LoreEntryResponse)
async def update_lore_entry(entry_id: int, entry: LoreEntryUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    db_entry = db.query(LoreEntry).filter(LoreEntry.id == entry_id).first()
    if not db_entry:
        raise HTTPException(status_code=404, detail="LoreEntry not found")
    for key, value in entry.dict(exclude_unset=True).items():
        setattr(db_entry, key, value)
    db.commit()
    db.refresh(db_entry)
    return db_entry

@app.delete("/api/lore-entries/{entry_id}")
async def delete_lore_entry(entry_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    entry = db.query(LoreEntry).filter(LoreEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="LoreEntry not found")
    db.delete(entry)
    db.commit()
    return {"message": "LoreEntry deleted"}

# ========== 角色-世界书绑定 API ==========

@app.get("/api/characters/{character_id}/worldbooks")
async def get_character_worldbooks(character_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    bindings = db.query(CharacterWorldBook).filter(CharacterWorldBook.character_id == character_id).all()
    wb_ids = [b.worldbook_id for b in bindings]
    wbs = db.query(WorldBook).filter(WorldBook.id.in_(wb_ids)).all()
    return [{"id": wb.id, "name": wb.name, "entry_count": len(wb.entries)} for wb in wbs]

@app.post("/api/characters/{character_id}/worldbooks/{worldbook_id}")
async def bind_worldbook(character_id: int, worldbook_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    existing = db.query(CharacterWorldBook).filter(
        CharacterWorldBook.character_id == character_id,
        CharacterWorldBook.worldbook_id == worldbook_id
    ).first()
    if existing:
        return {"message": "Already bound"}
    binding = CharacterWorldBook(character_id=character_id, worldbook_id=worldbook_id)
    db.add(binding)
    db.commit()
    return {"message": "Bound successfully"}

@app.delete("/api/characters/{character_id}/worldbooks/{worldbook_id}")
async def unbind_worldbook(character_id: int, worldbook_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    binding = db.query(CharacterWorldBook).filter(
        CharacterWorldBook.character_id == character_id,
        CharacterWorldBook.worldbook_id == worldbook_id
    ).first()
    if not binding:
        raise HTTPException(status_code=404, detail="Binding not found")
    db.delete(binding)
    db.commit()
    return {"message": "Unbound successfully"}

# ========== 聊天 API ==========

@app.get("/api/messages", response_model=List[MessageResponse])
async def get_messages(character_id: Optional[int] = None, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Message).filter(Message.user_id == current_user.id)
    if character_id:
        query = query.filter(Message.character_id == character_id)
    messages = query.order_by(Message.created_at.desc()).limit(limit).all()
    return list(reversed(messages))

@app.post("/api/chat")
async def chat(chat_request: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    character_id = chat_request.character_id
    if not character_id:
        char = db.query(Character).filter(Character.is_active == True).first()
        if not char:
            raise HTTPException(status_code=404, detail="No active character")
        character_id = char.id
    else:
        char = db.query(Character).filter(Character.id == character_id).first()
        if not char:
            raise HTTPException(status_code=404, detail="Character not found")
    
    # 保存用户消息
    user_msg = Message(user_id=current_user.id, character_id=character_id, content=chat_request.message, is_user=True)
    db.add(user_msg)
    update_intimacy(current_user, chat_request.message, db)
    
    # 获取历史对话
    history = db.query(Message).filter(
        Message.user_id == current_user.id,
        Message.character_id == character_id
    ).order_by(Message.created_at.desc()).limit(10).all()
    
    conversation_history = [{"role": "user" if m.is_user else "assistant", "content": m.content} for m in reversed(history)]
    
    # AI回复
    ai_response = await chat_with_ai(chat_request.message, char, current_user, db, conversation_history)
    
    ai_msg = Message(user_id=current_user.id, character_id=character_id, content=ai_response, is_user=False)
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)
    
    return {
        "user_message": MessageResponse.model_validate(user_msg),
        "ai_message": MessageResponse.model_validate(ai_msg)
    }

# ========== 用户管理 API（管理员） ==========

@app.get("/api/admin/users", response_model=List[UserAdminResponse])
async def list_users(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """管理员查看所有用户信息（包含密码哈希）"""
    return db.query(User).all()

@app.put("/api/admin/users/{user_id}/status")
async def update_user_status(user_id: int, status_update: UserStatusUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """更新用户状态（封号/解封）"""
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot modify yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = status_update.status
    user.ban_until = status_update.ban_until
    user.ban_reason = status_update.ban_reason
    db.commit()
    
    status_text = {"active": "正常", "temp_banned": "临时封禁", "banned": "永久封禁"}.get(status_update.status, status_update.status)
    return {"message": f"用户状态已更新为: {status_text}"}

@app.put("/api/admin/users/{user_id}/intimacy")
async def update_user_intimacy(user_id: int, intimacy_update: UserIntimacyUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """调整用户亲密度"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.intimacy = max(0.0, min(100.0, intimacy_update.intimacy))
    db.commit()
    return {"message": f"亲密度已调整为: {user.intimacy:.1f}"}

@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """删除用户"""
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

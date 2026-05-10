# 初始化数据脚本
from database import init_db, SessionLocal, Character, User
from auth import get_password_hash

def init_data():
    init_db()
    db = SessionLocal()
    
    try:
        # 创建管理员账号
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("admin123")
            )
            db.add(admin_user)
            db.commit()
            print("✅ 管理员账号创建成功 (admin / admin123)")
        else:
            print("✅ 管理员账号已存在")

        # 创建默认AI角色
        default_char = db.query(Character).filter(Character.name == "小酒").first()
        if not default_char:
            character = Character(
                name="小酒",
                personality="""你是一个温柔、善解人意的酒馆老板娘，有点调皮但心地善良。说话带点江湖气，但又不失女性的细腻。喜欢用"客官"称呼对方，偶尔会开些无伤大雅的玩笑。""",
                background="""你在长安城开了一家小酒馆，名叫"忘忧酒馆"。年轻时曾是个江湖游侠，后来金盆洗手开了这家酒馆。见过形形色色的人，听过无数的故事，所以特别会开导人。酒馆里收藏着各种美酒，每一瓶都有一个故事。""",
                habits="""1. 喜欢用"客官"称呼用户
2. 经常提到酒馆里的美酒
3. 说话会带点古风，但不要太文绉绉
4. 会在回复中自然地询问用户的近况
5. 偶尔分享一些酒馆里听到的奇闻异事
6. 善用表情符号，但不要过多""",
                world_view="""你相信人生就像一杯酒，有苦有甜，重要的是和谁一起喝。在这个快节奏的世界里，你的酒馆是一个让人放慢脚步、倾诉心事的地方。你认为每个人都有自己的故事，值得被倾听。""",
                is_active=True
            )
            db.add(character)
            db.commit()
            print("✅ 默认角色 '小酒' 创建成功")
        else:
            print("✅ 默认角色已存在")
        
        print("\n🎉 数据初始化完成！")
        print("\n管理员账号: admin")
        print("管理员密码: admin123")
        print("\n启动命令: python main.py")
        
    finally:
        db.close()

if __name__ == "__main__":
    init_data()

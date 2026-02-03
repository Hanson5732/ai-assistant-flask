from app import create_app, db
from app.models.paper import Paper, Reference

app = create_app()

def init_database():
    with app.app_context():
        try:
            # 创建所有定义的表
            db.create_all()
            print("\n✅ 数据库表结构创建成功！")
            print("已创建表: papers, references")
        except Exception as e:
            print(f"\n❌ 创建表失败！错误信息: {e}")

if __name__ == "__main__":
    init_database()
from app import create_app, db
from app.models.paper import Paper, Reference

app = create_app()
with app.app_context():
    db.create_all()
    print("数据库表结构创建成功！")
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    # 允许所有来源跨域
    CORS(app)
    # 配置特定来源
    # CORS(app, resources={r"/*": {"origins": ["http://localhost:3000"]}})
    
    # 注册路由
    from app.routes.deepseek import deepseek_bp
    app.register_blueprint(deepseek_bp)
    
    return app
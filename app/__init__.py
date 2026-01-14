from flask import Flask
from flask_cors import CORS

from app.routes.chat import chat_bp
from app.routes.process_paper import ocr_bp

def create_app():
    app = Flask(__name__)
    # 允许所有来源跨域
    CORS(app)
    # 配置特定来源
    # CORS(app, resources={r"/*": {"origins": ["http://localhost:3000"]}})

    # 注册路由
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(ocr_bp)

    
    return app
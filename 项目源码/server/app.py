"""
Flask应用入口
创建Flask实例，注册蓝图，初始化数据库和CORS
"""
import os
from flask import Flask
from flask_cors import CORS
from config import Config
from models import db
from utils.response import success


def create_app():
    """
    应用工厂函数
    创建并配置Flask应用实例
    :return: Flask应用实例
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # 配置 JSON 编码支持中文字符（解决 WHODrug/MedDRA 乱码问题）
    app.config['JSON_AS_ASCII'] = False
    app.json.ensure_ascii = False

    # 初始化数据库
    db.init_app(app)

    # 启用跨域支持
    CORS(app, supports_credentials=True)

    # 初始化 API 限流
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per minute"],
        storage_uri="memory://"
    )
    app.limiter = limiter

    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 注册蓝图（路由模块）
    from routes.auth import auth_bp
    from routes.knowledge_base import kb_bp
    from routes.document import doc_bp
    from routes.chat import chat_bp
    from routes.user import user_bp
    from routes.stats import stats_bp
    from routes.whodrug import whodrug_bp
    from routes.meddra import meddra_bp
    from routes.medical_import import medical_import_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(kb_bp, url_prefix='/api/knowledge_base')
    app.register_blueprint(doc_bp, url_prefix='/api/document')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(stats_bp, url_prefix='/api/stats')
    app.register_blueprint(whodrug_bp, url_prefix='/api/whodrug')
    app.register_blueprint(meddra_bp, url_prefix='/api/meddra')
    app.register_blueprint(medical_import_bp, url_prefix='/api/import')

    @app.get('/api/health')
    def health():
        return success({
            'service': 'backend',
            'status': 'ok'
        }, 'OK')

    # 对高消耗接口设置更严格的限流
    limiter.limit("10 per minute")(app.view_functions.get('chat.ask', lambda: None))
    limiter.limit("20 per minute")(app.view_functions.get('meddra.semantic_search', lambda: None))
    limiter.limit("5 per minute")(app.view_functions.get('meddra.explain_batch', lambda: None))

    return app


if __name__ == '__main__':
    app = create_app()
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5002))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(host=host, port=port, debug=debug)

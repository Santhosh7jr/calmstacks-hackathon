from flask import Flask
from flask_cors import CORS


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

    from app.routes.health import health_bp
    from app.routes.analyze import analyze_bp
    from app.routes.recovery import recovery_bp
    from app.routes.fragments import fragments_bp

    app.register_blueprint(health_bp, url_prefix="/api/health")
    app.register_blueprint(analyze_bp, url_prefix="/api/analyze")
    app.register_blueprint(recovery_bp, url_prefix="/api/recovery")
    app.register_blueprint(fragments_bp, url_prefix="/api/fragments")
    return app

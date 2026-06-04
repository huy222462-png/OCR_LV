from flask import Flask, redirect, url_for, session
from database import db
from config import Config
from backend.models import *
from backend.routes_auth import auth_bp
from backend.routes_document import document_bp
from backend.routes_admin import admin_bp
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(admin_bp)

    @app.route('/')
    def index():
        if session.get('user_id'):
            if session.get('chuc_vu') == 'QuanTriVien':
                return redirect(url_for('admin.admin_dashboard'))
            return redirect(url_for('auth.dashboard'))
        return redirect(url_for('auth.login'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)

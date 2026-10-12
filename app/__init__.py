"""Flask application factory."""

import os
from flask import Flask
from config import config_map


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map['development']))

    # Initialize extensions
    from app.extensions import db, login_manager, migrate, csrf
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Register blueprints
    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    from app.api.jobs import jobs_bp
    csrf.exempt(jobs_bp)
    app.register_blueprint(jobs_bp)

    from app.api.nodes import nodes_bp
    csrf.exempt(nodes_bp)
    app.register_blueprint(nodes_bp)

    from app.api.dashboard import dashboard_bp
    csrf.exempt(dashboard_bp)
    app.register_blueprint(dashboard_bp)

    from app.api.scheduling import scheduling_bp
    csrf.exempt(scheduling_bp)
    app.register_blueprint(scheduling_bp)

    # Register main page routes
    from app.views import main_bp
    app.register_blueprint(main_bp)

    # Import models to ensure they are registered with SQLAlchemy metadata
    with app.app_context():
        from app import models  # noqa: F401

    return app

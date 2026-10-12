"""Flask application configuration."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'db')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'cloudscheduler')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'changeme_db_password')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'cloud_scheduler')

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
    }

    # Worker settings
    WORKER_POLL_INTERVAL = int(os.environ.get('WORKER_POLL_INTERVAL', 5))
    WORKER_MAX_CONCURRENT = int(os.environ.get('WORKER_MAX_CONCURRENT', 3))
    CONTAINER_TIMEOUT = int(os.environ.get('CONTAINER_TIMEOUT', 300))
    CONTAINER_CLEANUP = os.environ.get('CONTAINER_CLEANUP', 'true').lower() == 'true'

    # Docker
    DOCKER_NETWORK = os.environ.get('DOCKER_NETWORK', 'cloud-scheduler-net')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}

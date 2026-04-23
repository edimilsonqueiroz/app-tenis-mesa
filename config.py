import os
from pathlib import Path

# Detectar ambiente
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development').lower()
IS_PRODUCTION = ENVIRONMENT in ('production', 'prod')
IS_DEVELOPMENT = not IS_PRODUCTION


class Config:
    """Base configuration"""
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY and IS_PRODUCTION:
        raise ValueError("SECRET_KEY environment variable must be set in production")
    if not SECRET_KEY:  # Development fallback
        SECRET_KEY = 'dev-secret-key-only-for-development'
    
    # Flask settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    
    # Database - automatically select based on environment
    if IS_PRODUCTION:
        # Production: PostgreSQL (required)
        DB_USER = os.environ.get('DB_USER', 'postgres')
        DB_PASSWORD = os.environ.get('DB_PASSWORD')
        DB_HOST = os.environ.get('DB_HOST', 'localhost')
        DB_PORT = os.environ.get('DB_PORT', '5432')
        DB_NAME = os.environ.get('DB_NAME', 'tenis_mesa')
        
        if not DB_PASSWORD:
            raise ValueError("DB_PASSWORD environment variable must be set in production")
        
        SQLALCHEMY_DATABASE_URI = (
            f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        )
    else:
        # Development: SQLite (local file)
        INSTANCE_PATH = Path(__file__).parent / 'instance'
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{INSTANCE_PATH}/tenis_mesa.db'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Select config based on environment
if ENVIRONMENT == 'testing':
    config = TestingConfig()
elif IS_PRODUCTION:
    config = ProductionConfig()
else:
    config = DevelopmentConfig()

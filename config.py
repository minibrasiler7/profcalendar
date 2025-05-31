import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Configuration générale
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Configuration base de données
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'database', 'teacher_planner.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuration session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Configuration WTForms
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None





































































from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Configuration initiale
    setup_completed = db.Column(db.Boolean, default=False)  # Configuration de base complétée
    schedule_completed = db.Column(db.Boolean, default=False)  # Horaire type complété
    school_year_start = db.Column(db.Date)
    school_year_end = db.Column(db.Date)

    # Horaires
    day_start_time = db.Column(db.Time)
    day_end_time = db.Column(db.Time)
    period_duration = db.Column(db.Integer)  # en minutes
    break_duration = db.Column(db.Integer)  # en minutes

    # Relations
    classrooms = db.relationship('Classroom', backref='teacher', lazy='dynamic', cascade='all, delete-orphan')
    holidays = db.relationship('Holiday', backref='teacher', lazy='dynamic', cascade='all, delete-orphan')
    breaks = db.relationship('Break', backref='teacher', lazy='dynamic', cascade='all, delete-orphan')
    schedules = db.relationship('Schedule', backref='teacher', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Holiday(db.Model):
    __tablename__ = 'holidays'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

class Break(db.Model):
    __tablename__ = 'breaks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_major_break = db.Column(db.Boolean, default=False)  # Grande pause comme pause midi

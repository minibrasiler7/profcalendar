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
    
    def get_id(self):
        """Retourne l'ID composite pour flask-login"""
        return f"teacher:{self.id}"

    def __repr__(self):
        return f'<User {self.username}>'
    
    # Méthodes pour le système de collaboration
    def is_master_of_class(self, classroom):
        """Vérifie si cet enseignant est maître de la classe donnée"""
        from models.class_collaboration import ClassMaster
        return ClassMaster.query.filter_by(
            master_teacher_id=self.id,
            classroom_id=classroom.id
        ).first() is not None
    
    def get_master_classes(self, school_year=None):
        """Retourne les classes dont cet enseignant est le maître"""
        from models.class_collaboration import ClassMaster
        query = ClassMaster.query.filter_by(master_teacher_id=self.id)
        if school_year:
            query = query.filter_by(school_year=school_year)
        return query.all()
    
    def get_collaborating_teachers(self):
        """Retourne les enseignants qui collaborent avec ce maître de classe"""
        from models.class_collaboration import TeacherCollaboration
        return TeacherCollaboration.query.filter_by(
            master_teacher_id=self.id,
            is_active=True
        ).all()
    
    def get_master_teacher(self):
        """Retourne le maître de classe avec qui cet enseignant collabore (s'il y en a un)"""
        from models.class_collaboration import TeacherCollaboration
        collaboration = TeacherCollaboration.query.filter_by(
            specialized_teacher_id=self.id,
            is_active=True
        ).first()
        return collaboration.master_teacher if collaboration else None
    
    def can_access_student_data(self, student, data_type='all'):
        """Vérifie si cet enseignant peut accéder aux données d'un élève"""
        # Si c'est le maître de classe de l'élève
        if student.classroom and self.is_master_of_class(student.classroom):
            return True
        
        # Si c'est un enseignant spécialisé qui enseigne à cet élève
        from models.class_collaboration import StudentClassroomLink
        student_link = StudentClassroomLink.query.filter_by(
            student_id=student.id,
            classroom_id__in=[c.id for c in self.classrooms]
        ).first()
        
        if student_link:
            # Accès limité selon le type de données demandé
            if data_type in ['grades', 'attendance', 'sanctions', 'all']:
                return True
        
        return False
    
    def generate_access_code(self, max_uses=None, expires_at=None):
        """Génère un nouveau code d'accès pour ce maître de classe"""
        from models.class_collaboration import TeacherAccessCode
        
        code = TeacherAccessCode(
            master_teacher_id=self.id,
            code=TeacherAccessCode.generate_code(),
            max_uses=max_uses,
            expires_at=expires_at
        )
        db.session.add(code)
        db.session.commit()
        return code

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

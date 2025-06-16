from extensions import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Parent(UserMixin, db.Model):
    """Modèle pour les parents"""
    __tablename__ = 'parents'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    
    # Informations de liaison avec l'enseignant
    teacher_name = db.Column(db.String(200))  # Nom de l'enseignant saisi par le parent
    class_code = db.Column(db.String(50))     # Code de classe saisi par le parent
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Lien vers l'enseignant une fois trouvé
    is_verified = db.Column(db.Boolean, default=False)  # Vérifié après attribution automatique
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relations
    teacher = db.relationship('User', backref=db.backref('parent_users', lazy='dynamic'))
    children = db.relationship('ParentChild', backref='parent', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        """Définir le mot de passe (hashé)"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Vérifier le mot de passe"""
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        """Retourne l'ID composite pour flask-login"""
        return f"parent:{self.id}"
    
    @property
    def full_name(self):
        """Nom complet du parent"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email.split('@')[0]  # Fallback sur la partie avant @ de l'email

    def __repr__(self):
        return f'<Parent {self.email}>'


class ParentChild(db.Model):
    """Table de liaison entre Parents et Élèves"""
    __tablename__ = 'parent_children'

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('parents.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    relationship = db.Column(db.String(20), default='parent')  # 'mother', 'father', 'parent', 'guardian'
    is_primary = db.Column(db.Boolean, default=True)  # Contact principal pour cet enfant
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    student = db.relationship('Student', backref=db.backref('parent_links', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('parent_id', 'student_id', name='_parent_child_uc'),
    )

    def __repr__(self):
        return f'<ParentChild {self.parent_id}-{self.student_id}>'


class ClassCode(db.Model):
    """Codes de classe pour faciliter l'inscription des parents"""
    __tablename__ = 'class_codes'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)  # Code unique pour la classe
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    classroom = db.relationship('Classroom', backref=db.backref('access_codes', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('class_codes', lazy='dynamic'))

    def __repr__(self):
        return f'<ClassCode {self.code} - {self.classroom.name}>'
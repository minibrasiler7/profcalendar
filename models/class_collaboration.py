from extensions import db
from datetime import datetime
import secrets
import string

class ClassMaster(db.Model):
    """Définit qui est maître de quelle classe"""
    __tablename__ = 'class_masters'
    
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    master_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    school_year = db.Column(db.String(20), nullable=False)  # Ex: "2024-2025"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    classroom = db.relationship('Classroom', backref='class_master_info')
    master_teacher = db.relationship('User', backref='master_classes')
    
    # Index unique pour éviter plusieurs maîtres pour la même classe la même année
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'school_year', name='unique_master_per_class_year'),
    )
    
    def __repr__(self):
        return f'<ClassMaster {self.master_teacher.username} - {self.classroom.name}>'

class TeacherAccessCode(db.Model):
    """Codes d'accès générés par les maîtres de classe"""
    __tablename__ = 'teacher_access_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    master_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    max_uses = db.Column(db.Integer, default=None)  # None = illimité
    current_uses = db.Column(db.Integer, default=0)
    expires_at = db.Column(db.DateTime, default=None)  # None = pas d'expiration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    master_teacher = db.relationship('User', backref='generated_access_codes')
    collaborations = db.relationship('TeacherCollaboration', backref='access_code')
    
    @staticmethod
    def generate_code(length=8):
        """Génère un code aléatoire unique"""
        characters = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(characters) for _ in range(length))
            if not TeacherAccessCode.query.filter_by(code=code).first():
                return code
    
    def is_valid(self):
        """Vérifie si le code est encore valide"""
        if not self.is_active:
            return False
        
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
            
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
            
        return True
    
    def use_code(self):
        """Utilise le code (incrémente le compteur)"""
        self.current_uses += 1
        db.session.commit()
    
    def __repr__(self):
        return f'<TeacherAccessCode {self.code} - {self.master_teacher.username}>'

class TeacherCollaboration(db.Model):
    """Collaboration entre enseignant spécialisé et maître de classe"""
    __tablename__ = 'teacher_collaborations'
    
    id = db.Column(db.Integer, primary_key=True)
    specialized_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    master_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    access_code_id = db.Column(db.Integer, db.ForeignKey('teacher_access_codes.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    specialized_teacher = db.relationship('User', foreign_keys=[specialized_teacher_id], backref='collaborations')
    master_teacher = db.relationship('User', foreign_keys=[master_teacher_id], backref='teacher_collaborations')
    
    # Index unique pour éviter les doublons
    __table_args__ = (
        db.UniqueConstraint('specialized_teacher_id', 'master_teacher_id', name='unique_collaboration'),
    )
    
    def __repr__(self):
        return f'<TeacherCollaboration {self.specialized_teacher.username} -> {self.master_teacher.username}>'

class SharedClassroom(db.Model):
    """Classes dérivées des classes du maître de classe"""
    __tablename__ = 'shared_classrooms'
    
    id = db.Column(db.Integer, primary_key=True)
    collaboration_id = db.Column(db.Integer, db.ForeignKey('teacher_collaborations.id'), nullable=False)
    original_classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    derived_classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)  # Matière enseignée
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    collaboration = db.relationship('TeacherCollaboration', backref='shared_classrooms')
    original_classroom = db.relationship('Classroom', foreign_keys=[original_classroom_id], backref='derived_from')
    derived_classroom = db.relationship('Classroom', foreign_keys=[derived_classroom_id], backref='derived_to')
    
    # Index unique pour éviter plusieurs classes dérivées pour la même collaboration/classe
    __table_args__ = (
        db.UniqueConstraint('collaboration_id', 'original_classroom_id', 'subject', name='unique_shared_classroom'),
    )
    
    def __repr__(self):
        return f'<SharedClassroom {self.derived_classroom.name} - {self.subject}>'

class StudentClassroomLink(db.Model):
    """Liens entre élèves et classes (permet de gérer les élèves partagés)"""
    __tablename__ = 'student_classroom_links'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)  # True pour la classe principale (maître de classe)
    added_by_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    student = db.relationship('Student', backref='classroom_links')
    classroom = db.relationship('Classroom', backref='student_links')
    added_by_teacher = db.relationship('User', backref='added_student_links')
    
    # Index unique pour éviter les doublons
    __table_args__ = (
        db.UniqueConstraint('student_id', 'classroom_id', 'subject', name='unique_student_classroom_subject'),
    )
    
    def __repr__(self):
        return f'<StudentClassroomLink {self.student.full_name} - {self.classroom.name} - {self.subject}>'
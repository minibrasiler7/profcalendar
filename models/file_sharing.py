from extensions import db
from datetime import datetime

class StudentFileShare(db.Model):
    """Modèle pour gérer le partage de fichiers entre enseignants et élèves"""
    __tablename__ = 'student_file_shares'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('class_files.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    shared_by_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shared_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    message = db.Column(db.Text)  # Message optionnel de l'enseignant
    viewed_at = db.Column(db.DateTime)  # Quand l'élève a vu le fichier
    
    # Relations
    file = db.relationship('ClassFile', backref='student_shares')
    student = db.relationship('Student', backref='shared_files')
    teacher = db.relationship('User', backref='shared_student_files')
    
    # Contrainte unique pour éviter les doublons
    __table_args__ = (
        db.UniqueConstraint('file_id', 'student_id', name='unique_file_student_share'),
    )
    
    def __repr__(self):
        return f'<StudentFileShare {self.file.original_filename} -> {self.student.full_name}>'
    
    def mark_as_viewed(self):
        """Marquer le fichier comme vu par l'élève"""
        if not self.viewed_at:
            self.viewed_at = datetime.utcnow()
            db.session.commit()
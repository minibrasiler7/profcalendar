from extensions import db
from datetime import datetime

class StudentInfoHistory(db.Model):
    """Modèle pour l'historique des informations supplémentaires d'un élève"""
    __tablename__ = 'student_info_history'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    student = db.relationship('Student', backref=db.backref('info_history', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('student_info_history', lazy='dynamic'))

    def __repr__(self):
        return f'<StudentInfoHistory {self.student_id} - {self.created_at}>'
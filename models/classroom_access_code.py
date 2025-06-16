from extensions import db
from datetime import datetime, timedelta

class ClassroomAccessCode(db.Model):
    __tablename__ = 'classroom_access_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    code = db.Column(db.String(6), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relations
    classroom = db.relationship('Classroom', backref='classroom_access_codes')
    created_by = db.relationship('User', backref='created_classroom_codes')
    
    def is_valid(self):
        """Vérifier si le code est valide"""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
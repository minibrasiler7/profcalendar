from extensions import db
from datetime import datetime, timedelta

class StudentAccessCode(db.Model):
    __tablename__ = 'student_access_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    code = db.Column(db.String(6), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    used_at = db.Column(db.DateTime)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relations
    student = db.relationship('Student', backref='student_access_codes')
    created_by = db.relationship('User', backref='created_student_codes')
    
    def is_valid(self):
        """Vérifier si le code est valide"""
        if self.used_at:
            return True  # Code déjà utilisé mais toujours valide pour reconnecter
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def use_code(self):
        """Marquer le code comme utilisé"""
        if not self.used_at:
            self.used_at = datetime.utcnow()
            db.session.commit()
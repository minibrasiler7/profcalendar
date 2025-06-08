from extensions import db
from datetime import datetime

class StudentSanctionCount(db.Model):
    """Compte des coches pour chaque élève par type de sanction"""
    __tablename__ = 'student_sanction_counts'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('sanction_templates.id'), nullable=False)
    check_count = db.Column(db.Integer, default=0, nullable=False)  # Nombre de coches actuelles
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    student = db.relationship('Student', backref='sanction_counts')
    template = db.relationship('SanctionTemplate', backref='student_counts')
    
    # Index unique pour éviter les doublons
    __table_args__ = (db.UniqueConstraint('student_id', 'template_id', name='unique_student_template'),)
    
    def __repr__(self):
        return f'<StudentSanctionCount {self.student.full_name} - {self.template.name}: {self.check_count}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'template_id': self.template_id,
            'check_count': self.check_count,
            'student_name': self.student.full_name,
            'template_name': self.template.name
        }
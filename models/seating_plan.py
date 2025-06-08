from extensions import db
from datetime import datetime

class SeatingPlan(db.Model):
    __tablename__ = 'seating_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False, default='Plan par défaut')
    plan_data = db.Column(db.Text, nullable=False)  # JSON stockant la configuration du plan
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    classroom = db.relationship('Classroom', backref='seating_plans')
    user = db.relationship('User', backref='seating_plans')
    
    def __repr__(self):
        return f'<SeatingPlan {self.name} for {self.classroom.name}>'
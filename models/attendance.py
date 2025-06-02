from extensions import db
from datetime import datetime

class Attendance(db.Model):
    """Modèle pour la gestion des présences/absences/retards"""
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    period_number = db.Column(db.Integer, nullable=False)

    # Status: 'present', 'absent', 'late'
    status = db.Column(db.String(20), nullable=False, default='present')

    # Minutes de retard (null si pas en retard)
    late_minutes = db.Column(db.Integer)

    # Commentaire optionnel
    comment = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    student = db.relationship('Student', backref=db.backref('attendances', lazy='dynamic'))
    classroom = db.relationship('Classroom', backref=db.backref('attendances', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('attendances', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('student_id', 'date', 'period_number', name='_student_date_period_uc'),
    )

    def __repr__(self):
        return f'<Attendance {self.student_id} - {self.date} P{self.period_number} - {self.status}>'

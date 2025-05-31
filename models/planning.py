from extensions import db
from datetime import datetime

class Planning(db.Model):
    """Planification spécifique pour une date donnée"""
    __tablename__ = 'plannings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)

    # Date spécifique
    date = db.Column(db.Date, nullable=False)

    # Numéro de la période
    period_number = db.Column(db.Integer, nullable=False)

    # Contenu de la planification
    title = db.Column(db.String(200))
    description = db.Column(db.Text)

    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relation avec l'utilisateur (en plus de celle héritée du modèle User)
    user = db.relationship('User', backref=db.backref('plannings', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', 'period_number', name='_user_date_period_uc'),
    )

    def __repr__(self):
        return f'<Planning {self.date} P{self.period_number} - {self.classroom.name}>'

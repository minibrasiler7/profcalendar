from extensions import db
from datetime import datetime

class Schedule(db.Model):
    """Horaire type hebdomadaire"""
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)

    # Jour de la semaine (0=Lundi, 1=Mardi, ..., 4=Vendredi)
    weekday = db.Column(db.Integer, nullable=False)

    # Numéro de la période dans la journée
    period_number = db.Column(db.Integer, nullable=False)

    # Heures calculées automatiquement basées sur la configuration utilisateur
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'weekday', 'period_number', name='_user_weekday_period_uc'),
    )

    def __repr__(self):
        days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
        return f'<Schedule {days[self.weekday]} P{self.period_number} - {self.classroom.name}>'

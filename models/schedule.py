from extensions import db
from datetime import datetime

class Schedule(db.Model):
    """Horaire type hebdomadaire"""
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Classe traditionnelle OU groupe mixte OU tâche personnalisée (l'un des trois doit être défini)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=True)
    mixed_group_id = db.Column(db.Integer, db.ForeignKey('mixed_groups.id'), nullable=True)
    
    # Tâche personnalisée (titre libre)
    custom_task_title = db.Column(db.String(255), nullable=True)

    # Jour de la semaine (0=Lundi, 1=Mardi, ..., 4=Vendredi)
    weekday = db.Column(db.Integer, nullable=False)

    # Numéro de la période dans la journée
    period_number = db.Column(db.Integer, nullable=False)

    # Heures calculées automatiquement basées sur la configuration utilisateur
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    # Note spécifique pour ce créneau (optionnel)
    notes = db.Column(db.Text)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'weekday', 'period_number', name='_user_weekday_period_uc'),
        db.CheckConstraint('(classroom_id IS NOT NULL AND mixed_group_id IS NULL AND custom_task_title IS NULL) OR (classroom_id IS NULL AND mixed_group_id IS NOT NULL AND custom_task_title IS NULL) OR (classroom_id IS NULL AND mixed_group_id IS NULL AND custom_task_title IS NOT NULL)', 
                          name='_classroom_or_mixed_group_or_custom'),
    )

    # Relations
    mixed_group = db.relationship('MixedGroup', backref=db.backref('schedules', lazy='dynamic'))

    def get_display_name(self):
        """Retourne le nom à afficher (classe, groupe mixte ou tâche personnalisée)"""
        if self.classroom_id:
            return self.classroom.name
        elif self.mixed_group_id:
            return self.mixed_group.name
        elif self.custom_task_title:
            return self.custom_task_title
        return "Non défini"
    
    def get_subject(self):
        """Retourne la matière enseignée"""
        if self.classroom_id:
            return self.classroom.subject
        elif self.mixed_group_id:
            return self.mixed_group.subject
        elif self.custom_task_title:
            return "Autre"
        return "Non défini"
    
    def get_students(self):
        """Retourne la liste des élèves concernés par ce créneau"""
        if self.classroom_id:
            return self.classroom.students.all()
        elif self.mixed_group_id:
            return self.mixed_group.get_students()
        elif self.custom_task_title:
            return []  # Pas d'élèves pour les tâches personnalisées
        return []
    
    def is_mixed_group(self):
        """Vérifie si ce créneau concerne un groupe mixte"""
        return self.mixed_group_id is not None
    
    def get_color(self):
        """Retourne la couleur pour l'affichage"""
        if self.classroom_id:
            return self.classroom.color
        elif self.mixed_group_id:
            return self.mixed_group.color
        elif self.custom_task_title:
            return '#6B7280'  # Couleur grise pour les tâches personnalisées
        return '#4a90e2'  # Couleur par défaut

    def __repr__(self):
        days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
        name = self.get_display_name()
        return f'<Schedule {days[self.weekday]} P{self.period_number} - {name}>'

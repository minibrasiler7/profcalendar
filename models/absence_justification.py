from extensions import db
from datetime import datetime

class AbsenceJustification(db.Model):
    """Modèle pour les justifications d'absence soumises par les parents"""
    __tablename__ = 'absence_justifications'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('parents.id'), nullable=False)
    
    # Informations sur l'absence
    absence_date = db.Column(db.Date, nullable=False)
    periods = db.Column(db.Text)  # JSON string avec les périodes [{"start": "08:00", "end": "09:00"}, ...]
    
    # Motif
    reason_type = db.Column(db.String(50), nullable=False)  # maladie, medecin, transport, conge_joker, dispense, autre
    other_reason_text = db.Column(db.Text)  # Texte libre si reason_type = 'autre'
    
    # Champs spécifiques pour les dispenses
    dispense_subject = db.Column(db.String(100))  # Discipline dispensée
    dispense_start_date = db.Column(db.Date)  # Date de début de dispense
    dispense_end_date = db.Column(db.Date)  # Date de fin de dispense
    
    # Fichier joint
    justification_file = db.Column(db.String(255))  # Nom du fichier uploadé
    
    # Statut de traitement
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    teacher_response = db.Column(db.Text)  # Réponse de l'enseignant
    processed_at = db.Column(db.DateTime)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    student = db.relationship('Student', backref=db.backref('justifications', lazy='dynamic'))
    parent = db.relationship('Parent', backref=db.backref('justifications', lazy='dynamic'))
    processed_by_teacher = db.relationship('User', backref=db.backref('processed_justifications', lazy='dynamic'))

    def get_periods_list(self):
        """Retourne la liste des périodes sous forme de dictionnaire"""
        import json
        if self.periods:
            try:
                return json.loads(self.periods)
            except:
                return []
        return []

    def set_periods_list(self, periods_list):
        """Définit la liste des périodes à partir d'un dictionnaire"""
        import json
        self.periods = json.dumps(periods_list)

    def get_reason_display(self):
        """Retourne le motif de l'absence en français"""
        reasons = {
            'maladie': 'Maladie/Accident',
            'medecin': 'Rendez-vous de médecin',
            'transport': 'Problème de transport',
            'conge_joker': 'Congé joker',
            'dispense': 'Dispense',
            'autre': 'Autre'
        }
        return reasons.get(self.reason_type, self.reason_type)

    def get_status_display(self):
        """Retourne le statut en français"""
        statuses = {
            'pending': 'En attente',
            'approved': 'Approuvée',
            'rejected': 'Refusée'
        }
        return statuses.get(self.status, self.status)

    def __repr__(self):
        return f'<AbsenceJustification {self.student.first_name} {self.student.last_name} - {self.absence_date}>'
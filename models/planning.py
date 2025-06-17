from extensions import db
from datetime import datetime
import json
import re

class Planning(db.Model):
    """Planification spécifique pour une date donnée"""
    __tablename__ = 'plannings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Classe traditionnelle OU groupe mixte (l'un des deux doit être défini)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=True)
    mixed_group_id = db.Column(db.Integer, db.ForeignKey('mixed_groups.id'), nullable=True)

    # Date spécifique
    date = db.Column(db.Date, nullable=False)

    # Numéro de la période
    period_number = db.Column(db.Integer, nullable=False)

    # Contenu de la planification
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    
    # Groupe spécifique (optionnel, si null = classe entière ou groupe mixte entier)
    group_id = db.Column(db.Integer, db.ForeignKey('student_groups.id'), nullable=True)

    # Nouveau champ pour stocker l'état des checkboxes (JSON)
    checklist_states = db.Column(db.Text)  # Stocké comme JSON

    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('plannings', lazy='dynamic'))
    group = db.relationship('StudentGroup', backref=db.backref('plannings', lazy='dynamic'))
    mixed_group = db.relationship('MixedGroup', backref=db.backref('plannings', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', 'period_number', name='_user_date_period_uc'),
        db.CheckConstraint('(classroom_id IS NOT NULL AND mixed_group_id IS NULL) OR (classroom_id IS NULL AND mixed_group_id IS NOT NULL)', 
                          name='_classroom_or_mixed_group_planning'),
    )

    def get_checklist_states(self):
        """Retourne les états des checkboxes comme dictionnaire"""
        if self.checklist_states:
            try:
                return json.loads(self.checklist_states)
            except:
                return {}
        return {}

    def set_checklist_states(self, states):
        """Définit les états des checkboxes depuis un dictionnaire"""
        self.checklist_states = json.dumps(states) if states else None

    def count_checklist_items(self):
        """Compte le nombre total de checkboxes dans la description"""
        if not self.description:
            return 0

        # Pattern pour détecter les checkboxes
        checkbox_pattern = r'^\s*\[([ x])\]\s*'
        lines = self.description.split('\n')
        count = 0

        for line in lines:
            if re.match(checkbox_pattern, line, re.IGNORECASE):
                count += 1

        return count

    def count_checked_items(self):
        """Compte le nombre de checkboxes cochées"""
        if not self.description:
            return 0

        states = self.get_checklist_states()
        if not states:
            return 0

        # Compter combien de valeurs True dans les états
        return sum(1 for value in states.values() if value is True)

    def get_checklist_summary(self):
        """Retourne un résumé des checkboxes (cochées/total)"""
        total = self.count_checklist_items()
        if total == 0:
            return None

        checked = self.count_checked_items()
        return {
            'total': total,
            'checked': checked,
            'percentage': (checked / total) * 100 if total > 0 else 0,
            'all_checked': checked == total
        }

    def get_checklist_items_with_states(self):
        """Retourne la liste des items de checklist avec leur état"""
        if not self.description:
            return []

        items = []
        states = self.get_checklist_states()
        checkbox_pattern = r'^(\s*)\[([ x])\]\s*(.*)$'
        lines = self.description.split('\n')
        checkbox_index = 0

        for line in lines:
            match = re.match(checkbox_pattern, line, re.IGNORECASE)
            if match:
                indent = match.group(1)
                content = match.group(3)
                is_checked = states.get(str(checkbox_index), False)

                items.append({
                    'index': checkbox_index,
                    'content': content,
                    'checked': is_checked,
                    'indent': len(indent)
                })

                checkbox_index += 1

        return items

    def get_display_name(self):
        """Retourne le nom à afficher (classe ou groupe mixte)"""
        if self.classroom_id:
            return self.classroom.name
        elif self.mixed_group_id:
            return self.mixed_group.name
        return "Non défini"
    
    def get_subject(self):
        """Retourne la matière enseignée"""
        if self.classroom_id:
            return self.classroom.subject
        elif self.mixed_group_id:
            return self.mixed_group.subject
        return "Non défini"
    
    def get_students(self):
        """Retourne la liste des élèves concernés par cette planification"""
        if self.group_id:
            # Si un groupe spécifique est défini, on utilise ce groupe
            return self.group.students.all()
        elif self.classroom_id:
            # Sinon, tous les élèves de la classe
            return self.classroom.students.all()
        elif self.mixed_group_id:
            # Ou tous les élèves du groupe mixte
            return self.mixed_group.get_students()
        return []
    
    def is_mixed_group(self):
        """Vérifie si cette planification concerne un groupe mixte"""
        return self.mixed_group_id is not None
    
    def get_color(self):
        """Retourne la couleur pour l'affichage"""
        if self.mixed_group_id:
            return self.mixed_group.color
        return '#4a90e2'  # Couleur par défaut pour les classes

    def __repr__(self):
        name = self.get_display_name()
        return f'<Planning {self.date} P{self.period_number} - {name}>'

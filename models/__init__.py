# Importer tous les modèles pour qu'ils soient disponibles
from models.user import User, Holiday, Break
from models.classroom import Classroom
from models.schedule import Schedule
from models.planning import Planning

__all__ = ['User', 'Holiday', 'Break', 'Classroom', 'Schedule', 'Planning']

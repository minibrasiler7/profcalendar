# Importer tous les modèles pour qu'ils soient disponibles
from models.user import User, Holiday, Break
from models.classroom import Classroom
from models.schedule import Schedule
from models.planning import Planning
from models.student import Student, Grade, ClassFile, Chapter, ClassroomChapter
from models.attendance import Attendance
from models.file_manager import FileFolder, UserFile, FileShare

__all__ = ['User', 'Holiday', 'Break', 'Classroom', 'Schedule', 'Planning',
           'Student', 'Grade', 'ClassFile', 'Chapter', 'ClassroomChapter', 'Attendance', 'FileFolder', 'UserFile', 'FileShare']

# Importer tous les modèles pour qu'ils soient disponibles
from models.user import User, Holiday, Break
from models.classroom import Classroom
from models.schedule import Schedule
from models.planning import Planning
from models.student import Student, Grade, ClassFile, Chapter, ClassroomChapter, StudentFile
from models.student_info_history import StudentInfoHistory
from models.attendance import Attendance
from models.file_manager import FileFolder, UserFile, FileShare
from models.sanctions import SanctionTemplate, SanctionThreshold, SanctionOption, ClassroomSanctionImport, StudentSanctionRecord
from models.student_sanctions import StudentSanctionCount
from models.evaluation import Evaluation, EvaluationGrade
from models.seating_plan import SeatingPlan
from models.student_group import StudentGroup, StudentGroupMembership
from models.class_collaboration import ClassMaster, TeacherAccessCode, TeacherCollaboration, SharedClassroom, StudentClassroomLink
from models.classroom_access_code import ClassroomAccessCode
from models.file_sharing import StudentFileShare

__all__ = ['User', 'Holiday', 'Break', 'Classroom', 'Schedule', 'Planning',
           'Student', 'Grade', 'ClassFile', 'Chapter', 'ClassroomChapter', 'StudentFile', 'StudentInfoHistory', 'Attendance', 'FileFolder', 'UserFile', 'FileShare',
           'SanctionTemplate', 'SanctionThreshold', 'SanctionOption', 'ClassroomSanctionImport', 'StudentSanctionRecord', 'StudentSanctionCount',
           'Evaluation', 'EvaluationGrade', 'SeatingPlan', 'StudentGroup', 'StudentGroupMembership',
           'ClassMaster', 'TeacherAccessCode', 'TeacherCollaboration', 'SharedClassroom', 'StudentClassroomLink',
           'ClassroomAccessCode', 'StudentFileShare']

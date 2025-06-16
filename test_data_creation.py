#!/usr/bin/env python3
"""
Script de création de données de test pour ProfCalendar
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from models.user import User
from models.parent import Parent, ParentChild, ClassCode
from models.classroom import Classroom
from models.student import Student
from models.class_collaboration import ClassMaster, TeacherAccessCode, TeacherCollaboration, SharedClassroom
from models.evaluation import Evaluation, EvaluationGrade
from models.attendance import Attendance
from models.student_sanctions import StudentSanctionCount
from models.sanctions import SanctionTemplate
from datetime import datetime, date, time
import random

def create_test_data():
    """Créer des données de test complètes"""
    
    with app.app_context():
        print("🧹 Nettoyage des données existantes...")
        # Nettoyer les données existantes (optionnel)
        # db.drop_all()
        # db.create_all()
        
        print("👨‍🏫 Création des enseignants...")
        
        # Enseignant 1 - Maître de classe (Math)
        teacher1 = User(
            username="prof_martin",
            email="martin@school.com",
            setup_completed=True,
            schedule_completed=True,
            day_start_time=time(7, 30),
            day_end_time=time(16, 30),
            period_duration=45,
            break_duration=15,
            school_year_start=date(2024, 8, 15),
            school_year_end=date(2025, 6, 30)
        )
        teacher1.set_password("password123")
        db.session.add(teacher1)
        
        # Enseignant 2 - Maître de classe (Français)
        teacher2 = User(
            username="prof_durand",
            email="durand@school.com",
            setup_completed=True,
            schedule_completed=True,
            day_start_time=time(7, 30),
            day_end_time=time(16, 30),
            period_duration=45,
            break_duration=15,
            school_year_start=date(2024, 8, 15),
            school_year_end=date(2025, 6, 30)
        )
        teacher2.set_password("password123")
        db.session.add(teacher2)
        
        # Enseignant 3 - Enseignant spécialisé (Sport)
        teacher3 = User(
            username="prof_sport",
            email="sport@school.com",
            setup_completed=True,
            schedule_completed=True,
            day_start_time=time(7, 30),
            day_end_time=time(16, 30),
            period_duration=45,
            break_duration=15,
            school_year_start=date(2024, 8, 15),
            school_year_end=date(2025, 6, 30)
        )
        teacher3.set_password("password123")
        db.session.add(teacher3)
        
        # Enseignant 4 - Enseignant normal (Anglais)
        teacher4 = User(
            username="prof_smith",
            email="smith@school.com",
            setup_completed=True,
            schedule_completed=True,
            day_start_time=time(7, 30),
            day_end_time=time(16, 30),
            period_duration=45,
            break_duration=15,
            school_year_start=date(2024, 8, 15),
            school_year_end=date(2025, 6, 30)
        )
        teacher4.set_password("password123")
        db.session.add(teacher4)
        
        db.session.commit()
        
        print("🏫 Création des classes...")
        
        # Classes pour teacher1 (Math)
        class1 = Classroom(user_id=teacher1.id, name="6ème A", subject="Mathématiques", color="#3498db")
        class2 = Classroom(user_id=teacher1.id, name="5ème B", subject="Mathématiques", color="#2980b9")
        
        # Classes pour teacher2 (Français)
        class3 = Classroom(user_id=teacher2.id, name="6ème A", subject="Français", color="#e74c3c")
        class4 = Classroom(user_id=teacher2.id, name="4ème C", subject="Français", color="#c0392b")
        
        # Classes pour teacher4 (Anglais)
        class5 = Classroom(user_id=teacher4.id, name="3ème D", subject="Anglais", color="#f39c12")
        
        db.session.add_all([class1, class2, class3, class4, class5])
        db.session.commit()
        
        print("👑 Création des maîtrises de classe...")
        
        # Teacher1 devient maître de sa classe 6ème A (Math)
        master1 = ClassMaster(
            classroom_id=class1.id,
            master_teacher_id=teacher1.id,
            school_year="2024-2025"
        )
        
        # Teacher2 devient maître de sa classe 6ème A (Français)
        master2 = ClassMaster(
            classroom_id=class3.id,
            master_teacher_id=teacher2.id,
            school_year="2024-2025"
        )
        
        db.session.add_all([master1, master2])
        db.session.commit()
        
        print("👶 Création des élèves...")
        
        # Élèves pour la classe 6ème A Math (teacher1)
        students_class1 = [
            Student(classroom_id=class1.id, user_id=teacher1.id, first_name="Alice", last_name="Martin", 
                   email="alice.martin@student.com", date_of_birth=date(2012, 3, 15),
                   parent_email_mother="marie.martin@parent.com", parent_email_father="paul.martin@parent.com"),
            Student(classroom_id=class1.id, user_id=teacher1.id, first_name="Bob", last_name="Durand", 
                   email="bob.durand@student.com", date_of_birth=date(2012, 7, 22),
                   parent_email_mother="sophie.durand@parent.com", parent_email_father="pierre.durand@parent.com"),
            Student(classroom_id=class1.id, user_id=teacher1.id, first_name="Claire", last_name="Petit", 
                   email="claire.petit@student.com", date_of_birth=date(2012, 11, 8),
                   parent_email_mother="anne.petit@parent.com", parent_email_father="michel.petit@parent.com"),
        ]
        
        # Élèves pour la classe 6ème A Français (teacher2)  
        students_class3 = [
            Student(classroom_id=class3.id, user_id=teacher2.id, first_name="Alice", last_name="Martin", 
                   email="alice.martin@student.com", date_of_birth=date(2012, 3, 15),
                   parent_email_mother="marie.martin@parent.com", parent_email_father="paul.martin@parent.com"),
            Student(classroom_id=class3.id, user_id=teacher2.id, first_name="Bob", last_name="Durand", 
                   email="bob.durand@student.com", date_of_birth=date(2012, 7, 22),
                   parent_email_mother="sophie.durand@parent.com", parent_email_father="pierre.durand@parent.com"),
            Student(classroom_id=class3.id, user_id=teacher2.id, first_name="David", last_name="Moreau", 
                   email="david.moreau@student.com", date_of_birth=date(2012, 5, 18),
                   parent_email_mother="laura.moreau@parent.com", parent_email_father="thomas.moreau@parent.com"),
        ]
        
        # Élèves pour la classe 5ème B (teacher1)
        students_class2 = [
            Student(classroom_id=class2.id, user_id=teacher1.id, first_name="Emma", last_name="Bernard", 
                   email="emma.bernard@student.com", date_of_birth=date(2011, 4, 12),
                   parent_email_mother="julie.bernard@parent.com", parent_email_father="luc.bernard@parent.com"),
            Student(classroom_id=class2.id, user_id=teacher1.id, first_name="Hugo", last_name="Rousseau", 
                   email="hugo.rousseau@student.com", date_of_birth=date(2011, 9, 30),
                   parent_email_mother="claire.rousseau@parent.com", parent_email_father="antoine.rousseau@parent.com"),
        ]
        
        db.session.add_all(students_class1 + students_class3 + students_class2)
        db.session.commit()
        
        print("👨‍👩‍👧‍👦 Création des parents...")
        
        # Parents
        parents_data = [
            ("marie.martin@parent.com", "Marie", "Martin", "password123"),
            ("sophie.durand@parent.com", "Sophie", "Durand", "password123"),
            ("anne.petit@parent.com", "Anne", "Petit", "password123"),
            ("laura.moreau@parent.com", "Laura", "Moreau", "password123"),
            ("julie.bernard@parent.com", "Julie", "Bernard", "password123"),
            ("claire.rousseau@parent.com", "Claire", "Rousseau", "password123"),
        ]
        
        parents = []
        for email, first_name, last_name, password in parents_data:
            parent = Parent(email=email, first_name=first_name, last_name=last_name)
            parent.set_password(password)
            parents.append(parent)
        
        db.session.add_all(parents)
        db.session.commit()
        
        print("🔗 Création des codes de classe et liaison parents...")
        
        # Codes de classe
        code1 = ClassCode(code="MATH6A", user_id=teacher1.id, classroom_id=class1.id, is_active=True)
        code2 = ClassCode(code="FR6A", user_id=teacher2.id, classroom_id=class3.id, is_active=True)
        code3 = ClassCode(code="MATH5B", user_id=teacher1.id, classroom_id=class2.id, is_active=True)
        
        db.session.add_all([code1, code2, code3])
        db.session.commit()
        
        # Liaison automatique des parents aux enseignants
        for parent in parents:
            if parent.email == "marie.martin@parent.com":
                parent.teacher_id = teacher1.id
                parent.teacher_name = teacher1.username
                parent.class_code = "MATH6A"
            elif parent.email == "sophie.durand@parent.com":
                parent.teacher_id = teacher2.id
                parent.teacher_name = teacher2.username  
                parent.class_code = "FR6A"
            elif parent.email == "anne.petit@parent.com":
                parent.teacher_id = teacher1.id
                parent.teacher_name = teacher1.username
                parent.class_code = "MATH6A"
            elif parent.email == "julie.bernard@parent.com":
                parent.teacher_id = teacher1.id
                parent.teacher_name = teacher1.username
                parent.class_code = "MATH5B"
        
        db.session.commit()
        
        # Liens parent-enfant
        parent_child_links = [
            (parents[0].id, students_class1[0].id, "mother"),  # Marie -> Alice (Math)
            (parents[1].id, students_class1[1].id, "mother"),  # Sophie -> Bob (Math)
            (parents[2].id, students_class1[2].id, "mother"),  # Anne -> Claire (Math)
            (parents[3].id, students_class3[2].id, "mother"),  # Laura -> David (Français)
            (parents[4].id, students_class2[0].id, "mother"),  # Julie -> Emma (5ème)
            (parents[5].id, students_class2[1].id, "mother"),  # Claire -> Hugo (5ème)
        ]
        
        for parent_id, student_id, relationship in parent_child_links:
            link = ParentChild(parent_id=parent_id, student_id=student_id, relationship=relationship, is_primary=True)
            db.session.add(link)
        
        db.session.commit()
        
        print("🤝 Création des collaborations enseignants...")
        
        # Teacher1 (maître) génère un code d'accès
        access_code = TeacherAccessCode(
            master_teacher_id=teacher1.id,
            code="SPORT2024",
            max_uses=5,
            expires_at=None,
            is_active=True
        )
        db.session.add(access_code)
        db.session.commit()
        
        # Teacher3 (sport) se lie à teacher1
        collaboration = TeacherCollaboration(
            specialized_teacher_id=teacher3.id,
            master_teacher_id=teacher1.id,
            access_code_id=access_code.id
        )
        db.session.add(collaboration)
        db.session.commit()
        
        # Classe dérivée pour le sport basée sur 6ème A Math
        derived_classroom = Classroom(
            user_id=teacher3.id,
            name="6ème A - Sport",
            subject="Education Physique",
            color="#27ae60"
        )
        db.session.add(derived_classroom)
        db.session.commit()
        
        # Lien classe partagée
        shared_classroom = SharedClassroom(
            collaboration_id=collaboration.id,
            original_classroom_id=class1.id,
            derived_classroom_id=derived_classroom.id,
            subject="Education Physique"
        )
        db.session.add(shared_classroom)
        db.session.commit()
        
        # Copier les élèves dans la classe dérivée
        for student in students_class1:
            derived_student = Student(
                classroom_id=derived_classroom.id,
                user_id=teacher3.id,
                first_name=student.first_name,
                last_name=student.last_name,
                email=student.email,
                date_of_birth=student.date_of_birth,
                parent_email_mother=student.parent_email_mother,
                parent_email_father=student.parent_email_father
            )
            db.session.add(derived_student)
        
        db.session.commit()
        
        print("📊 Création des évaluations et notes...")
        
        # Évaluations pour Math 6ème A
        eval1 = Evaluation(
            classroom_id=class1.id,
            title="Contrôle Fractions",
            type="significatif",
            date=date(2024, 10, 15),
            max_points=20
        )
        
        eval2 = Evaluation(
            classroom_id=class1.id,
            title="TA Calcul Mental",
            type="ta",
            ta_group_name="Calcul",
            date=date(2024, 10, 8),
            max_points=10
        )
        
        eval3 = Evaluation(
            classroom_id=class1.id,
            title="TA Géométrie",
            type="ta", 
            ta_group_name="Géométrie",
            date=date(2024, 10, 22),
            max_points=10
        )
        
        # Évaluations pour Français 6ème A
        eval4 = Evaluation(
            classroom_id=class3.id,
            title="Dictée",
            type="significatif",
            date=date(2024, 10, 12),
            max_points=20
        )
        
        eval5 = Evaluation(
            classroom_id=class3.id,
            title="TA Conjugaison",
            type="ta",
            ta_group_name="Grammaire",
            date=date(2024, 10, 5),
            max_points=10
        )
        
        # Évaluations pour Sport (classe dérivée)
        eval6 = Evaluation(
            classroom_id=derived_classroom.id,
            title="Course 50m",
            type="significatif",
            date=date(2024, 10, 18),
            max_points=20
        )
        
        db.session.add_all([eval1, eval2, eval3, eval4, eval5, eval6])
        db.session.commit()
        
        # Notes pour les élèves
        all_students = students_class1 + students_class3 + students_class2
        
        # Notes Math pour class1
        for i, student in enumerate(students_class1):
            # Note contrôle fractions
            grade1 = EvaluationGrade(
                evaluation_id=eval1.id,
                student_id=student.id,
                points=random.randint(12, 19)
            )
            # Note TA calcul
            grade2 = EvaluationGrade(
                evaluation_id=eval2.id,
                student_id=student.id,
                points=random.randint(6, 10)
            )
            # Note TA géométrie
            grade3 = EvaluationGrade(
                evaluation_id=eval3.id,
                student_id=student.id,
                points=random.randint(7, 10)
            )
            db.session.add_all([grade1, grade2, grade3])
        
        # Notes Français pour class3
        for i, student in enumerate(students_class3):
            # Note dictée
            grade4 = EvaluationGrade(
                evaluation_id=eval4.id,
                student_id=student.id,
                points=random.randint(10, 18)
            )
            # Note TA conjugaison
            grade5 = EvaluationGrade(
                evaluation_id=eval5.id,
                student_id=student.id,
                points=random.randint(5, 10)
            )
            db.session.add_all([grade4, grade5])
        
        # Notes Sport pour classe dérivée
        derived_students = Student.query.filter_by(classroom_id=derived_classroom.id).all()
        for student in derived_students:
            grade6 = EvaluationGrade(
                evaluation_id=eval6.id,
                student_id=student.id,
                points=random.randint(14, 20)
            )
            db.session.add(grade6)
        
        db.session.commit()
        
        print("⚠️ Création des sanctions et coches...")
        
        # Templates de sanctions
        template1 = SanctionTemplate(
            teacher_id=teacher1.id,
            name="Bavardage",
            description="Parle pendant le cours"
        )
        
        template2 = SanctionTemplate(
            teacher_id=teacher1.id,
            name="Oubli matériel",
            description="A oublié ses affaires"
        )
        
        template3 = SanctionTemplate(
            teacher_id=teacher2.id,
            name="Retard",
            description="Arrivé en retard"
        )
        
        db.session.add_all([template1, template2, template3])
        db.session.commit()
        
        # Coches pour quelques élèves
        sanctions_data = [
            (students_class1[0].id, template1.id, 2),  # Alice: 2 bavardages
            (students_class1[1].id, template1.id, 1),  # Bob: 1 bavardage  
            (students_class1[1].id, template2.id, 3),  # Bob: 3 oublis matériel
            (students_class3[0].id, template3.id, 1),  # Alice: 1 retard en français
        ]
        
        for student_id, template_id, count in sanctions_data:
            sanction = StudentSanctionCount(
                student_id=student_id,
                template_id=template_id,
                check_count=count
            )
            db.session.add(sanction)
        
        db.session.commit()
        
        print("📅 Création des données de présence...")
        
        # Quelques absences/retards
        attendance_data = [
            (students_class1[0].id, class1.id, date(2024, 10, 14), 1, "absent", None, "Maladie"),
            (students_class1[1].id, class1.id, date(2024, 10, 14), 2, "late", 10, "Transport"),
            (students_class3[2].id, class3.id, date(2024, 10, 13), 1, "absent", None, "Rendez-vous médical"),
        ]
        
        for student_id, classroom_id, att_date, period, status, late_min, comment in attendance_data:
            attendance = Attendance(
                student_id=student_id,
                classroom_id=classroom_id,
                date=att_date,
                period_number=period,
                status=status,
                late_minutes=late_min,
                comment=comment
            )
            db.session.add(attendance)
        
        db.session.commit()
        
        print("✅ Données de test créées avec succès!")
        print("\n📋 RÉSUMÉ DES COMPTES CRÉÉS:")
        print("\n👨‍🏫 ENSEIGNANTS:")
        print("• prof_martin (martin@school.com) - Maître de classe Math 6ème A")
        print("• prof_durand (durand@school.com) - Maître de classe Français 6ème A") 
        print("• prof_sport (sport@school.com) - Enseignant spécialisé Sport")
        print("• prof_smith (smith@school.com) - Enseignant Anglais")
        print("\n👨‍👩‍👧‍👦 PARENTS:")
        print("• marie.martin@parent.com - Mère d'Alice")
        print("• sophie.durand@parent.com - Mère de Bob")
        print("• anne.petit@parent.com - Mère de Claire")
        print("• laura.moreau@parent.com - Mère de David")
        print("• julie.bernard@parent.com - Mère d'Emma")
        print("• claire.rousseau@parent.com - Mère d'Hugo")
        print("\n🎓 ÉLÈVES:")
        print("• Alice Martin (6ème A Math & Français)")
        print("• Bob Durand (6ème A Math & Français)")
        print("• Claire Petit (6ème A Math)")
        print("• David Moreau (6ème A Français)")
        print("• Emma Bernard (5ème B Math)")
        print("• Hugo Rousseau (5ème B Math)")
        print("\n🤝 COLLABORATIONS:")
        print("• prof_sport collabore avec prof_martin (classe dérivée Sport)")
        print("\n🔑 Mot de passe pour tous les comptes: password123")

if __name__ == "__main__":
    create_test_data()
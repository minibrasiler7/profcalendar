-- Script SQL pour créer des données de test ProfCalendar
-- À exécuter après avoir lancé l'application une première fois

-- Enseignants de test
INSERT INTO users (username, email, password_hash, setup_completed, schedule_completed, day_start_time, day_end_time, period_duration, break_duration, school_year_start, school_year_end) VALUES
('prof_martin', 'martin@school.com', 'pbkdf2:sha256:600000$salt$hash', 1, 1, '07:30:00', '16:30:00', 45, 15, '2024-08-15', '2025-06-30'),
('prof_durand', 'durand@school.com', 'pbkdf2:sha256:600000$salt$hash', 1, 1, '07:30:00', '16:30:00', 45, 15, '2024-08-15', '2025-06-30'),
('prof_sport', 'sport@school.com', 'pbkdf2:sha256:600000$salt$hash', 1, 1, '07:30:00', '16:30:00', 45, 15, '2024-08-15', '2025-06-30');

-- Classes
INSERT INTO classrooms (user_id, name, subject, color) VALUES
(1, '6ème A', 'Mathématiques', '#3498db'),
(2, '6ème A', 'Français', '#e74c3c'),
(3, '6ème A - Sport', 'Education Physique', '#27ae60');

-- Maîtrises de classe
INSERT INTO class_masters (classroom_id, master_teacher_id, school_year) VALUES
(1, 1, '2024-2025'),
(2, 2, '2024-2025');

-- Collaboration (prof_sport avec prof_martin)
INSERT INTO teacher_access_codes (master_teacher_id, code, is_active, created_at) VALUES
(1, 'SPORT2024', 1, datetime('now'));

INSERT INTO teacher_collaborations (specialized_teacher_id, master_teacher_id, access_code_id, is_active) VALUES
(3, 1, 1, 1);

INSERT INTO shared_classrooms (collaboration_id, original_classroom_id, derived_classroom_id, subject) VALUES
(1, 1, 3, 'Education Physique');

-- Élèves
INSERT INTO students (classroom_id, user_id, first_name, last_name, email, date_of_birth, parent_email_mother, parent_email_father) VALUES
(1, 1, 'Alice', 'Martin', 'alice.martin@student.com', '2012-03-15', 'marie.martin@parent.com', 'paul.martin@parent.com'),
(1, 1, 'Bob', 'Durand', 'bob.durand@student.com', '2012-07-22', 'sophie.durand@parent.com', 'pierre.durand@parent.com'),
(2, 2, 'Alice', 'Martin', 'alice.martin@student.com', '2012-03-15', 'marie.martin@parent.com', 'paul.martin@parent.com'),
(3, 3, 'Alice', 'Martin', 'alice.martin@student.com', '2012-03-15', 'marie.martin@parent.com', 'paul.martin@parent.com'),
(3, 3, 'Bob', 'Durand', 'bob.durand@student.com', '2012-07-22', 'sophie.durand@parent.com', 'pierre.durand@parent.com');

-- Parents
INSERT INTO parents (email, first_name, last_name, password_hash, teacher_id, teacher_name, class_code, is_verified) VALUES
('marie.martin@parent.com', 'Marie', 'Martin', 'pbkdf2:sha256:600000$salt$hash', 1, 'prof_martin', 'MATH6A', 1),
('sophie.durand@parent.com', 'Sophie', 'Durand', 'pbkdf2:sha256:600000$salt$hash', 1, 'prof_martin', 'MATH6A', 1);

-- Liens parent-enfant
INSERT INTO parent_children (parent_id, student_id, relationship, is_primary) VALUES
(1, 1, 'mother', 1),  -- Marie -> Alice (Math)
(1, 3, 'mother', 1),  -- Marie -> Alice (Français)
(1, 4, 'mother', 1),  -- Marie -> Alice (Sport)
(2, 2, 'mother', 1),  -- Sophie -> Bob (Math)
(2, 5, 'mother', 1);  -- Sophie -> Bob (Sport)

-- Codes de classe
INSERT INTO class_codes (code, user_id, classroom_id, is_active) VALUES
('MATH6A', 1, 1, 1),
('FR6A', 2, 2, 1);

-- Évaluations
INSERT INTO evaluations (classroom_id, title, type, date, max_points, ta_group_name) VALUES
(1, 'Contrôle Fractions', 'significatif', '2024-10-15', 20, NULL),
(1, 'TA Calcul', 'ta', '2024-10-08', 10, 'Calcul'),
(2, 'Dictée', 'significatif', '2024-10-12', 20, NULL),
(3, 'Course 50m', 'significatif', '2024-10-18', 20, NULL);

-- Notes
INSERT INTO evaluation_grades (evaluation_id, student_id, points) VALUES
(1, 1, 16),  -- Alice Math: 16/20
(2, 1, 8),   -- Alice TA Math: 8/10
(3, 3, 14),  -- Alice Français: 14/20
(4, 4, 18);  -- Alice Sport: 18/20

-- Présences
INSERT INTO attendances (student_id, classroom_id, date, period_number, status, comment) VALUES
(1, 1, '2024-10-14', 1, 'absent', 'Maladie'),
(4, 3, '2024-10-16', 2, 'late', 'Transport');

-- Templates de sanctions
INSERT INTO sanction_templates (teacher_id, name, description) VALUES
(1, 'Bavardage', 'Parle pendant le cours'),
(1, 'Oubli matériel', 'A oublié ses affaires');

-- Coches
INSERT INTO student_sanction_counts (student_id, template_id, check_count) VALUES
(1, 1, 2),  -- Alice: 2 bavardages
(2, 2, 1);  -- Bob: 1 oubli

-- Mots de passe pour tous les comptes: password123
-- Hash généré avec: generate_password_hash("password123")
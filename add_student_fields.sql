-- Script pour ajouter les nouveaux champs au modèle Student

-- Ajouter la colonne user_id à la table students
ALTER TABLE students ADD COLUMN user_id INTEGER;

-- Ajouter la colonne additional_info à la table students
ALTER TABLE students ADD COLUMN additional_info TEXT;

-- Mettre à jour user_id pour tous les élèves existants en se basant sur leur classe
UPDATE students 
SET user_id = (
    SELECT classrooms.user_id 
    FROM classrooms 
    WHERE classrooms.id = students.classroom_id
);

-- Créer la table student_files
CREATE TABLE IF NOT EXISTS student_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);
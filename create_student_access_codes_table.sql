-- Créer la table des codes d'accès élèves
CREATE TABLE IF NOT EXISTS student_access_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    code VARCHAR(6) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    used_at TIMESTAMP,
    created_by_user_id INTEGER NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users (id)
);

-- Créer un index sur le code pour des recherches rapides
CREATE INDEX IF NOT EXISTS idx_student_access_codes_code ON student_access_codes(code);

-- Créer un index sur student_id
CREATE INDEX IF NOT EXISTS idx_student_access_codes_student_id ON student_access_codes(student_id);

-- Ajouter les colonnes pour l'authentification des élèves dans la table students
ALTER TABLE students ADD COLUMN password_hash VARCHAR(255);
ALTER TABLE students ADD COLUMN is_authenticated BOOLEAN DEFAULT 0;
ALTER TABLE students ADD COLUMN last_login TIMESTAMP;
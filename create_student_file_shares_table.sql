-- Création de la table pour le partage de fichiers avec les élèves
CREATE TABLE IF NOT EXISTS student_file_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    shared_by_teacher_id INTEGER NOT NULL,
    shared_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    message TEXT,
    viewed_at DATETIME,
    FOREIGN KEY (file_id) REFERENCES class_files (id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    FOREIGN KEY (shared_by_teacher_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE(file_id, student_id)
);
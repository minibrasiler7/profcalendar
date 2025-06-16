-- Tables pour le système de collaboration entre enseignants

-- Table pour définir qui est maître de quelle classe
CREATE TABLE IF NOT EXISTS class_masters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER NOT NULL,
    master_teacher_id INTEGER NOT NULL,
    school_year VARCHAR(20) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE,
    FOREIGN KEY (master_teacher_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE (classroom_id, school_year)
);

-- Table pour les codes d'accès générés par les maîtres de classe
CREATE TABLE IF NOT EXISTS teacher_access_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    master_teacher_id INTEGER NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    max_uses INTEGER DEFAULT NULL,
    current_uses INTEGER DEFAULT 0,
    expires_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (master_teacher_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Table pour les collaborations entre enseignants
CREATE TABLE IF NOT EXISTS teacher_collaborations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    specialized_teacher_id INTEGER NOT NULL,
    master_teacher_id INTEGER NOT NULL,
    access_code_id INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (specialized_teacher_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (master_teacher_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (access_code_id) REFERENCES teacher_access_codes (id) ON DELETE CASCADE,
    UNIQUE (specialized_teacher_id, master_teacher_id)
);

-- Table pour les classes dérivées/partagées
CREATE TABLE IF NOT EXISTS shared_classrooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collaboration_id INTEGER NOT NULL,
    original_classroom_id INTEGER NOT NULL,
    derived_classroom_id INTEGER NOT NULL,
    subject VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (collaboration_id) REFERENCES teacher_collaborations (id) ON DELETE CASCADE,
    FOREIGN KEY (original_classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE,
    FOREIGN KEY (derived_classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE,
    UNIQUE (collaboration_id, original_classroom_id, subject)
);

-- Table pour gérer les liens entre élèves et classes (pour élèves partagés)
CREATE TABLE IF NOT EXISTS student_classroom_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    classroom_id INTEGER NOT NULL,
    subject VARCHAR(100) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    added_by_teacher_id INTEGER NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    FOREIGN KEY (classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE,
    FOREIGN KEY (added_by_teacher_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE (student_id, classroom_id, subject)
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_class_masters_teacher ON class_masters (master_teacher_id);
CREATE INDEX IF NOT EXISTS idx_class_masters_classroom ON class_masters (classroom_id);
CREATE INDEX IF NOT EXISTS idx_access_codes_teacher ON teacher_access_codes (master_teacher_id);
CREATE INDEX IF NOT EXISTS idx_access_codes_code ON teacher_access_codes (code);
CREATE INDEX IF NOT EXISTS idx_collaborations_specialized ON teacher_collaborations (specialized_teacher_id);
CREATE INDEX IF NOT EXISTS idx_collaborations_master ON teacher_collaborations (master_teacher_id);
CREATE INDEX IF NOT EXISTS idx_shared_classrooms_collaboration ON shared_classrooms (collaboration_id);
CREATE INDEX IF NOT EXISTS idx_student_links_student ON student_classroom_links (student_id);
CREATE INDEX IF NOT EXISTS idx_student_links_classroom ON student_classroom_links (classroom_id);
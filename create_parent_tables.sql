-- Créer les tables pour le système parents

-- Table des parents
CREATE TABLE IF NOT EXISTS parents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    teacher_name VARCHAR(200),
    class_code VARCHAR(50),
    teacher_id INTEGER,
    is_verified BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    FOREIGN KEY (teacher_id) REFERENCES users (id)
);

-- Table de liaison parents-enfants
CREATE TABLE IF NOT EXISTS parent_children (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    relationship VARCHAR(20) DEFAULT 'parent',
    is_primary BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES parents (id),
    FOREIGN KEY (student_id) REFERENCES students (id),
    UNIQUE(parent_id, student_id)
);

-- Table des codes de classe
CREATE TABLE IF NOT EXISTS class_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (classroom_id) REFERENCES classrooms (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Créer des index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_parents_email ON parents(email);
CREATE INDEX IF NOT EXISTS idx_parents_teacher ON parents(teacher_id);
CREATE INDEX IF NOT EXISTS idx_parent_children_parent ON parent_children(parent_id);
CREATE INDEX IF NOT EXISTS idx_parent_children_student ON parent_children(student_id);
CREATE INDEX IF NOT EXISTS idx_class_codes_code ON class_codes(code);
CREATE INDEX IF NOT EXISTS idx_class_codes_classroom ON class_codes(classroom_id);
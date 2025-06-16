-- Créer la table des codes d'accès de classe
CREATE TABLE IF NOT EXISTS classroom_access_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER NOT NULL,
    code VARCHAR(6) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    created_by_user_id INTEGER NOT NULL,
    FOREIGN KEY (classroom_id) REFERENCES classrooms (id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users (id)
);

-- Créer un index sur le code pour des recherches rapides
CREATE INDEX IF NOT EXISTS idx_classroom_access_codes_code ON classroom_access_codes(code);

-- Créer un index sur classroom_id
CREATE INDEX IF NOT EXISTS idx_classroom_access_codes_classroom_id ON classroom_access_codes(classroom_id);
-- Créer la table pour les justifications d'absence
CREATE TABLE IF NOT EXISTS absence_justifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    parent_id INTEGER NOT NULL,
    
    -- Informations sur l'absence
    absence_date DATE NOT NULL,
    periods TEXT,  -- JSON string avec les périodes
    
    -- Motif
    reason_type VARCHAR(50) NOT NULL,
    other_reason_text TEXT,
    
    -- Champs spécifiques pour les dispenses
    dispense_subject VARCHAR(100),
    dispense_start_date DATE,
    dispense_end_date DATE,
    
    -- Fichier joint
    justification_file VARCHAR(255),
    
    -- Statut de traitement
    status VARCHAR(20) DEFAULT 'pending',
    teacher_response TEXT,
    processed_at DATETIME,
    processed_by INTEGER,
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (student_id) REFERENCES students (id),
    FOREIGN KEY (parent_id) REFERENCES parents (id),
    FOREIGN KEY (processed_by) REFERENCES users (id)
);

-- Créer des index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_justifications_student ON absence_justifications(student_id);
CREATE INDEX IF NOT EXISTS idx_justifications_parent ON absence_justifications(parent_id);
CREATE INDEX IF NOT EXISTS idx_justifications_date ON absence_justifications(absence_date);
CREATE INDEX IF NOT EXISTS idx_justifications_status ON absence_justifications(status);
-- Script pour créer les tables des aménagements

-- Table des modèles d'aménagements
CREATE TABLE IF NOT EXISTS accommodation_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    emoji VARCHAR(10) NOT NULL,
    category VARCHAR(100),
    is_time_extension BOOLEAN DEFAULT 0,
    time_multiplier REAL,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Table des aménagements assignés aux élèves
CREATE TABLE IF NOT EXISTS student_accommodations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    template_id INTEGER,
    custom_name VARCHAR(200),
    custom_description TEXT,
    custom_emoji VARCHAR(10),
    custom_is_time_extension BOOLEAN DEFAULT 0,
    custom_time_multiplier REAL,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (student_id) REFERENCES students (id),
    FOREIGN KEY (template_id) REFERENCES accommodation_templates (id)
);

-- Insertion des aménagements prédéfinis pour tous les utilisateurs existants
INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension, time_multiplier)
SELECT 
    u.id,
    'Temps prolongé (+50%)',
    'L''élève bénéficie de 50% de temps supplémentaire pour les évaluations',
    '⏰',
    'Temps',
    1,
    1.5
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Temps prolongé (+50%)'
);

INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension, time_multiplier)
SELECT 
    u.id,
    'Temps prolongé (+33%)',
    'L''élève bénéficie d''un tiers de temps supplémentaire pour les évaluations',
    '⏰',
    'Temps',
    1,
    1.33
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Temps prolongé (+33%)'
);

INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension, time_multiplier)
SELECT 
    u.id,
    'Temps prolongé (+25%)',
    'L''élève bénéficie d''un quart de temps supplémentaire pour les évaluations',
    '⏰',
    'Temps',
    1,
    1.25
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Temps prolongé (+25%)'
);

INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension)
SELECT 
    u.id,
    'Reformulation des consignes',
    'Les consignes doivent être reformulées et expliquées à l''élève',
    '💬',
    'Consignes',
    0
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Reformulation des consignes'
);

INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension)
SELECT 
    u.id,
    'Vérifier la compréhension',
    'S''assurer que l''élève a bien compris les consignes avant de commencer',
    '✅',
    'Consignes',
    0
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Vérifier la compréhension'
);

INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension)
SELECT 
    u.id,
    'Document de référence',
    'L''élève a le droit à un document de référence pendant l''évaluation',
    '📄',
    'Matériel',
    0
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Document de référence'
);

INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension)
SELECT 
    u.id,
    'Dictionnaire autorisé',
    'L''élève a le droit d''utiliser un dictionnaire',
    '📚',
    'Matériel',
    0
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Dictionnaire autorisé'
);

INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension)
SELECT 
    u.id,
    'Tablette autorisée',
    'L''élève peut utiliser une tablette pour l''évaluation',
    '📱',
    'Matériel',
    0
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Tablette autorisée'
);

INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension)
SELECT 
    u.id,
    'Casque anti-bruit',
    'L''élève a besoin d''un casque pour bloquer les bruits environnants',
    '🎧',
    'Environnement',
    0
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Casque anti-bruit'
);

INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension)
SELECT 
    u.id,
    'Orthographe non évaluée',
    'L''orthographe ne doit pas être comptabilisée dans la note',
    '📝',
    'Évaluation',
    0
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Orthographe non évaluée'
);

INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension)
SELECT 
    u.id,
    'Document format A3',
    'Le document doit être imprimé en format A3',
    '📏',
    'Format',
    0
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Document format A3'
);

INSERT INTO accommodation_templates (user_id, name, description, emoji, category, is_time_extension)
SELECT 
    u.id,
    'Police lisible et aérée',
    'La police d''écriture doit être lisible et le texte bien aéré',
    '🔤',
    'Format',
    0
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM accommodation_templates 
    WHERE user_id = u.id AND name = 'Police lisible et aérée'
);
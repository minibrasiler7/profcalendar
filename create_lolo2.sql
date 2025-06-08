-- Créer l'utilisateur lolo2 basé sur lolo strauch
-- D'abord, supprimer l'utilisateur s'il existe déjà
DELETE FROM users WHERE username = 'lolo2';

-- Insérer le nouvel utilisateur avec un hash de mot de passe pour "lolo2"
INSERT INTO users (
    username, 
    email, 
    password_hash, 
    created_at, 
    setup_completed, 
    schedule_completed, 
    school_year_start, 
    school_year_end, 
    day_start_time, 
    day_end_time, 
    period_duration, 
    break_duration
) VALUES (
    'lolo2',
    'lolo2@example.com',
    'scrypt:32768:8:1$lolo2password$6dae3cfe3c94c6ba00af17664bfc6e1852a184e4fbb7a87a25b35147827eb240160532dcad2b6703697b4d22d97ed0a119b437dd771f5db1c292d7022141a629',
    datetime('now'),
    1,  -- setup_completed
    1,  -- schedule_completed
    '2024-08-19',  -- school_year_start
    '2025-06-27',  -- school_year_end
    '07:40:00.000000',  -- day_start_time
    '16:20:00.000000',  -- day_end_time
    45,  -- period_duration
    5   -- break_duration
);

-- Obtenir l'ID du nouvel utilisateur
-- Copier les vacances
INSERT INTO holidays (user_id, name, start_date, end_date)
SELECT 
    (SELECT id FROM users WHERE username = 'lolo2') as user_id,
    name,
    start_date,
    end_date
FROM holidays 
WHERE user_id = (SELECT id FROM users WHERE username = 'lolo strauch');

-- Copier les pauses
INSERT INTO breaks (user_id, name, start_time, end_time, is_major_break)
SELECT 
    (SELECT id FROM users WHERE username = 'lolo2') as user_id,
    name,
    start_time,
    end_time,
    is_major_break
FROM breaks 
WHERE user_id = (SELECT id FROM users WHERE username = 'lolo strauch');

-- Copier les classes
INSERT INTO classrooms (user_id, name, subject, color)
SELECT 
    (SELECT id FROM users WHERE username = 'lolo2') as user_id,
    name,
    subject,
    color
FROM classrooms 
WHERE user_id = (SELECT id FROM users WHERE username = 'lolo strauch');

-- Copier les horaires (avec correspondance des IDs de classes)
INSERT INTO schedules (user_id, classroom_id, weekday, period_number, start_time, end_time)
SELECT 
    (SELECT id FROM users WHERE username = 'lolo2') as user_id,
    new_classrooms.id as classroom_id,
    old_schedules.weekday,
    old_schedules.period_number,
    old_schedules.start_time,
    old_schedules.end_time
FROM schedules old_schedules
JOIN classrooms old_classrooms ON old_schedules.classroom_id = old_classrooms.id
JOIN classrooms new_classrooms ON new_classrooms.name = old_classrooms.name AND new_classrooms.user_id = (SELECT id FROM users WHERE username = 'lolo2')
WHERE old_schedules.user_id = (SELECT id FROM users WHERE username = 'lolo strauch');

-- Afficher le résultat
SELECT 'Utilisateur lolo2 créé avec ID: ' || id as result FROM users WHERE username = 'lolo2';
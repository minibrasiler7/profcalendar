-- Vérifier les collaborations actives
SELECT 
    tc.id,
    u1.username as specialized_teacher,
    u2.username as master_teacher,
    tc.is_active,
    tc.joined_at
FROM teacher_collaborations tc
JOIN users u1 ON tc.specialized_teacher_id = u1.id
JOIN users u2 ON tc.master_teacher_id = u2.id
WHERE tc.is_active = 1;

-- Vérifier les maîtres de classe
SELECT 
    cm.id,
    u.username as master_teacher,
    c.name as classroom_name,
    cm.school_year
FROM class_masters cm
JOIN users u ON cm.master_teacher_id = u.id
JOIN classrooms c ON cm.classroom_id = c.id;
-- Ajouter les champs email des parents à la table students
ALTER TABLE students ADD COLUMN parent_email_mother VARCHAR(120);
ALTER TABLE students ADD COLUMN parent_email_father VARCHAR(120);
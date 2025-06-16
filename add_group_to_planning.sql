-- Script pour ajouter la colonne group_id à la table plannings
ALTER TABLE plannings ADD COLUMN group_id INTEGER REFERENCES student_groups(id);
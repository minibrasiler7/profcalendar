#!/usr/bin/env python3
"""
Générer un hash de mot de passe pour l'utilisateur lolo2
"""

# Utiliser la même méthode que Flask/Werkzeug
from werkzeug.security import generate_password_hash

# Générer le hash pour le mot de passe "lolo2"
password = "lolo2"
password_hash = generate_password_hash(password)

print(f"Hash du mot de passe pour '{password}':")
print(password_hash)
print("\nPour mettre à jour dans la base de données:")
print(f"UPDATE users SET password_hash = '{password_hash}' WHERE username = 'lolo2';")
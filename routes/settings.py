from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models.user_preferences import UserPreferences
from models.parent import ClassCode
from models.classroom import Classroom
import secrets
import string

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@login_required
def index():
    """Page principale des paramètres utilisateur"""
    # Récupérer ou créer les préférences de l'utilisateur
    preferences = UserPreferences.get_or_create_for_user(current_user.id)
    
    return render_template('settings/index.html', preferences=preferences)

@settings_bp.route('/update-accommodations-display', methods=['POST'])
@login_required
def update_accommodations_display():
    """Mettre à jour les préférences d'affichage des aménagements"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
    
    show_accommodations = data.get('show_accommodations')
    
    if show_accommodations not in ['none', 'emoji', 'name']:
        return jsonify({'success': False, 'message': 'Valeur invalide'}), 400
    
    try:
        # Récupérer ou créer les préférences
        preferences = UserPreferences.get_or_create_for_user(current_user.id)
        
        # Mettre à jour la préférence
        preferences.show_accommodations = show_accommodations
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Préférences mises à jour avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@settings_bp.route('/class-codes')
@login_required
def class_codes():
    """Gestion des codes de classe pour les parents"""
    # Récupérer tous les codes de classe de l'utilisateur
    codes = ClassCode.query.filter_by(user_id=current_user.id).all()
    
    # Récupérer toutes les classes de l'utilisateur
    classrooms = current_user.classrooms.all()
    
    return render_template('settings/class_codes.html', codes=codes, classrooms=classrooms)

@settings_bp.route('/generate-class-code', methods=['POST'])
@login_required
def generate_class_code():
    """Générer un nouveau code de classe"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
    
    classroom_id = data.get('classroom_id')
    
    if not classroom_id:
        return jsonify({'success': False, 'message': 'ID de classe requis'}), 400
    
    # Vérifier que la classe appartient à l'utilisateur
    classroom = Classroom.query.filter_by(id=classroom_id, user_id=current_user.id).first()
    if not classroom:
        return jsonify({'success': False, 'message': 'Classe non trouvée'}), 404
    
    try:
        # Désactiver les anciens codes pour cette classe
        ClassCode.query.filter_by(classroom_id=classroom_id, user_id=current_user.id).update({
            'is_active': False
        })
        
        # Générer un nouveau code unique
        while True:
            # Génération d'un code de 6 caractères (lettres et chiffres)
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            
            # Vérifier que le code n'existe pas déjà
            existing = ClassCode.query.filter_by(code=code).first()
            if not existing:
                break
        
        # Créer le nouveau code
        new_code = ClassCode(
            classroom_id=classroom_id,
            user_id=current_user.id,
            code=code,
            is_active=True
        )
        
        db.session.add(new_code)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Nouveau code généré avec succès',
            'code': code,
            'classroom_name': classroom.name
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@settings_bp.route('/deactivate-class-code/<int:code_id>', methods=['POST'])
@login_required
def deactivate_class_code(code_id):
    """Désactiver un code de classe"""
    # Vérifier que le code appartient à l'utilisateur
    code = ClassCode.query.filter_by(id=code_id, user_id=current_user.id).first()
    
    if not code:
        return jsonify({'success': False, 'message': 'Code non trouvé'}), 404
    
    try:
        code.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Code désactivé avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
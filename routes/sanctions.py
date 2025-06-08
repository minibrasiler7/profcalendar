from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.sanctions import SanctionTemplate, SanctionThreshold, SanctionOption, ClassroomSanctionImport
from models.classroom import Classroom
from datetime import datetime

sanctions_bp = Blueprint('sanctions', __name__, url_prefix='/sanctions')

@sanctions_bp.route('/')
@login_required
def index():
    """Page principale de gestion des sanctions"""
    # Vérifier que la configuration de base est complète
    if not current_user.setup_completed:
        flash('Veuillez d\'abord compléter la configuration initiale.', 'warning')
        return redirect(url_for('setup.initial_setup'))
    
    # Récupérer tous les modèles de sanctions de l'utilisateur
    templates = SanctionTemplate.query.filter_by(
        user_id=current_user.id
    ).order_by(SanctionTemplate.name).all()
    
    # Préparer les templates avec les seuils triés
    for template in templates:
        # Charger les seuils triés par check_count
        template.sorted_thresholds = SanctionThreshold.query.filter_by(
            template_id=template.id
        ).order_by(SanctionThreshold.check_count).all()
    
    # Récupérer les classes pour l'import
    classrooms = current_user.classrooms.all()
    
    # Statistiques
    total_templates = len(templates)
    active_templates = len([t for t in templates if t.is_active])
    total_imports = ClassroomSanctionImport.query.join(SanctionTemplate).filter(
        SanctionTemplate.user_id == current_user.id
    ).count()
    
    stats = {
        'total_templates': total_templates,
        'active_templates': active_templates,
        'total_imports': total_imports
    }
    
    return render_template('sanctions/index.html',
                         templates=templates,
                         classrooms=classrooms,
                         stats=stats)

@sanctions_bp.route('/create')
@login_required
def create():
    """Formulaire de création d'un nouveau modèle"""
    return render_template('sanctions/create.html')

@sanctions_bp.route('/edit/<int:template_id>')
@login_required
def edit(template_id):
    """Formulaire d'édition d'un modèle"""
    template = SanctionTemplate.query.filter_by(
        id=template_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Récupérer tous les seuils avec leurs sanctions
    thresholds = SanctionThreshold.query.filter_by(
        template_id=template.id
    ).order_by(SanctionThreshold.check_count).all()
    
    return render_template('sanctions/edit.html',
                         template=template,
                         thresholds=thresholds)

@sanctions_bp.route('/save', methods=['POST'])
@login_required
def save():
    """Sauvegarder un modèle de sanction"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
    
    try:
        template_id = data.get('template_id')
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        thresholds_data = data.get('thresholds', [])
        
        if not name:
            return jsonify({'success': False, 'message': 'Le nom est obligatoire'}), 400
        
        if not thresholds_data:
            return jsonify({'success': False, 'message': 'Au moins un seuil est requis'}), 400
        
        # Créer ou mettre à jour le template
        if template_id:
            template = SanctionTemplate.query.filter_by(
                id=template_id,
                user_id=current_user.id
            ).first()
            if not template:
                return jsonify({'success': False, 'message': 'Modèle non trouvé'}), 404
            template.updated_at = datetime.utcnow()
        else:
            template = SanctionTemplate(user_id=current_user.id)
            db.session.add(template)
        
        template.name = name
        template.description = description
        
        # Supprimer les anciens seuils si on modifie
        if template_id:
            SanctionThreshold.query.filter_by(template_id=template.id).delete()
        
        db.session.flush()  # Pour obtenir l'ID du template
        
        # Créer les nouveaux seuils
        for threshold_data in thresholds_data:
            check_count = threshold_data.get('check_count')
            sanctions_data = threshold_data.get('sanctions', [])
            
            if not check_count or not sanctions_data:
                continue
            
            threshold = SanctionThreshold(
                template_id=template.id,
                check_count=check_count
            )
            db.session.add(threshold)
            db.session.flush()  # Pour obtenir l'ID du seuil
            
            # Créer les sanctions pour ce seuil
            for i, sanction_data in enumerate(sanctions_data):
                description = sanction_data.get('description', '').strip()
                min_days = sanction_data.get('min_days_deadline')
                
                if not description:
                    continue
                
                # Convertir en entier si fourni, sinon garder None
                if min_days is not None and min_days != '':
                    try:
                        min_days = int(min_days)
                    except (ValueError, TypeError):
                        min_days = None
                else:
                    min_days = None
                
                sanction = SanctionOption(
                    threshold_id=threshold.id,
                    description=description,
                    min_days_deadline=min_days,
                    order_index=i
                )
                db.session.add(sanction)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Modèle sauvegardé avec succès',
            'template_id': template.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@sanctions_bp.route('/delete/<int:template_id>', methods=['DELETE'])
@login_required
def delete(template_id):
    """Supprimer un modèle de sanction"""
    try:
        template = SanctionTemplate.query.filter_by(
            id=template_id,
            user_id=current_user.id
        ).first()
        
        if not template:
            return jsonify({'success': False, 'message': 'Modèle non trouvé'}), 404
        
        # Vérifier s'il y a des imports actifs
        active_imports = ClassroomSanctionImport.query.filter_by(
            template_id=template.id,
            is_active=True
        ).count()
        
        if active_imports > 0:
            return jsonify({
                'success': False, 
                'message': f'Impossible de supprimer : ce modèle est utilisé dans {active_imports} classe(s)'
            }), 400
        
        db.session.delete(template)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Modèle supprimé avec succès'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@sanctions_bp.route('/toggle-status/<int:template_id>', methods=['POST'])
@login_required
def toggle_status(template_id):
    """Activer/désactiver un modèle"""
    try:
        template = SanctionTemplate.query.filter_by(
            id=template_id,
            user_id=current_user.id
        ).first()
        
        if not template:
            return jsonify({'success': False, 'message': 'Modèle non trouvé'}), 404
        
        template.is_active = not template.is_active
        template.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = 'activé' if template.is_active else 'désactivé'
        return jsonify({
            'success': True, 
            'message': f'Modèle {status} avec succès',
            'is_active': template.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@sanctions_bp.route('/import-to-class', methods=['POST'])
@login_required
def import_to_class():
    """Importer un modèle vers une ou plusieurs classes"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
    
    try:
        template_id = data.get('template_id')
        classroom_ids = data.get('classroom_ids', [])
        
        if not template_id or not classroom_ids:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400
        
        # Vérifier que le template appartient à l'utilisateur
        template = SanctionTemplate.query.filter_by(
            id=template_id,
            user_id=current_user.id
        ).first()
        
        if not template:
            return jsonify({'success': False, 'message': 'Modèle non trouvé'}), 404
        
        imported_count = 0
        already_imported = 0
        
        for classroom_id in classroom_ids:
            # Vérifier que la classe appartient à l'utilisateur
            classroom = Classroom.query.filter_by(
                id=classroom_id,
                user_id=current_user.id
            ).first()
            
            if not classroom:
                continue
            
            # Vérifier si déjà importé
            existing = ClassroomSanctionImport.query.filter_by(
                classroom_id=classroom_id,
                template_id=template_id
            ).first()
            
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    existing.updated_at = datetime.utcnow()
                    imported_count += 1
                else:
                    already_imported += 1
            else:
                # Créer nouvel import
                import_record = ClassroomSanctionImport(
                    classroom_id=classroom_id,
                    template_id=template_id
                )
                db.session.add(import_record)
                imported_count += 1
        
        db.session.commit()
        
        message = f'Modèle importé dans {imported_count} classe(s)'
        if already_imported > 0:
            message += f' ({already_imported} déjà importé(s))'
        
        return jsonify({
            'success': True,
            'message': message,
            'imported_count': imported_count,
            'already_imported': already_imported
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@sanctions_bp.route('/get-template/<int:template_id>')
@login_required
def get_template(template_id):
    """Récupérer les détails d'un modèle pour l'édition"""
    try:
        template = SanctionTemplate.query.filter_by(
            id=template_id,
            user_id=current_user.id
        ).first()
        
        if not template:
            return jsonify({'success': False, 'message': 'Modèle non trouvé'}), 404
        
        # Récupérer les seuils avec leurs sanctions
        thresholds = []
        for threshold in template.thresholds.order_by(SanctionThreshold.check_count).all():
            sanctions = []
            for sanction in threshold.sanctions.order_by(SanctionOption.order_index).all():
                sanctions.append(sanction.to_dict())
            
            thresholds.append({
                'id': threshold.id,
                'check_count': threshold.check_count,
                'sanctions': sanctions
            })
        
        return jsonify({
            'success': True,
            'template': {
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'is_active': template.is_active,
                'thresholds': thresholds
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@sanctions_bp.route('/class-imports/<int:classroom_id>')
@login_required
def class_imports(classroom_id):
    """Voir les modèles importés dans une classe"""
    # Vérifier que la classe appartient à l'utilisateur
    classroom = Classroom.query.filter_by(
        id=classroom_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Récupérer les imports actifs
    imports = ClassroomSanctionImport.query.filter_by(
        classroom_id=classroom_id,
        is_active=True
    ).join(SanctionTemplate).filter(
        SanctionTemplate.user_id == current_user.id
    ).all()
    
    return render_template('sanctions/class_imports.html',
                         classroom=classroom,
                         imports=imports)
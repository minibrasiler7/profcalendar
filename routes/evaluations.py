from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.evaluation import Evaluation, EvaluationGrade
from models.classroom import Classroom
from models.student import Student
from datetime import datetime

evaluations_bp = Blueprint('evaluations', __name__, url_prefix='/api/evaluations')

@evaluations_bp.route('/classroom/<int:classroom_id>')
@login_required
def get_classroom_evaluations(classroom_id):
    """Récupérer toutes les évaluations d'une classe"""
    try:
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=classroom_id,
            user_id=current_user.id
        ).first()
        
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404
        
        # Récupérer toutes les évaluations avec leurs notes
        evaluations = Evaluation.query.filter_by(classroom_id=classroom_id).order_by(Evaluation.date.desc()).all()
        
        evaluations_data = []
        ta_groups = set()
        
        for evaluation in evaluations:
            # Récupérer les notes de cette évaluation
            grades = EvaluationGrade.query.filter_by(evaluation_id=evaluation.id).all()
            grades_data = []
            
            for grade in grades:
                grades_data.append({
                    'student_id': grade.student_id,
                    'points': grade.points
                })
            
            evaluation_data = {
                'id': evaluation.id,
                'title': evaluation.title,
                'type': evaluation.type,
                'ta_group_name': evaluation.ta_group_name,
                'date': evaluation.date.isoformat() if evaluation.date else None,
                'max_points': evaluation.max_points,
                'min_points': evaluation.min_points,
                'grades': grades_data,
                'average': evaluation.get_average()
            }
            
            evaluations_data.append(evaluation_data)
            
            # Collecter les groupes TA
            if evaluation.ta_group_name:
                ta_groups.add(evaluation.ta_group_name)
        
        return jsonify({
            'success': True,
            'evaluations': evaluations_data,
            'ta_groups': list(ta_groups)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@evaluations_bp.route('/create', methods=['POST'])
@login_required
def create_evaluation():
    """Créer une nouvelle évaluation avec ses notes"""
    try:
        data = request.get_json()
        
        classroom_id = data.get('classroom_id')
        title = data.get('title', '').strip()
        date_str = data.get('date')
        max_points = data.get('max_points')
        min_points = data.get('min_points', 0)
        eval_type = data.get('type')
        ta_group_name = data.get('ta_group_name', '').strip() if data.get('ta_group_name') else None
        grades_data = data.get('grades', [])
        
        # Validation
        if not all([classroom_id, title, date_str, max_points, eval_type]):
            return jsonify({'success': False, 'message': 'Paramètres manquants'}), 400
        
        if eval_type not in ['significatif', 'ta']:
            return jsonify({'success': False, 'message': 'Type d\'évaluation invalide'}), 400
        
        if eval_type == 'ta' and not ta_group_name:
            return jsonify({'success': False, 'message': 'Nom du groupe TA requis'}), 400
        
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=classroom_id,
            user_id=current_user.id
        ).first()
        
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404
        
        # Convertir la date
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Format de date invalide'}), 400
        
        # Créer l'évaluation
        evaluation = Evaluation(
            classroom_id=classroom_id,
            title=title,
            type=eval_type,
            ta_group_name=ta_group_name,
            date=date,
            max_points=float(max_points),
            min_points=float(min_points)
        )
        
        db.session.add(evaluation)
        db.session.flush()  # Pour obtenir l'ID
        
        # Créer les notes
        for grade_data in grades_data:
            student_id = grade_data.get('student_id')
            points = grade_data.get('points')
            
            if student_id and points is not None:
                # Vérifier que l'élève appartient à cette classe
                student = Student.query.filter_by(
                    id=student_id,
                    classroom_id=classroom_id
                ).first()
                
                if student:
                    grade = EvaluationGrade(
                        evaluation_id=evaluation.id,
                        student_id=student_id,
                        points=float(points)
                    )
                    db.session.add(grade)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Évaluation créée avec succès',
            'evaluation': {
                'id': evaluation.id,
                'title': evaluation.title,
                'type': evaluation.type,
                'ta_group_name': evaluation.ta_group_name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@evaluations_bp.route('/<int:evaluation_id>')
@login_required
def get_evaluation(evaluation_id):
    """Récupérer une évaluation spécifique"""
    try:
        # Vérifier que l'évaluation appartient à une classe de l'utilisateur
        evaluation = db.session.query(Evaluation).join(
            Classroom, Evaluation.classroom_id == Classroom.id
        ).filter(
            Evaluation.id == evaluation_id,
            Classroom.user_id == current_user.id
        ).first()
        
        if not evaluation:
            return jsonify({'success': False, 'message': 'Évaluation introuvable'}), 404
        
        # Récupérer les notes
        grades = EvaluationGrade.query.filter_by(evaluation_id=evaluation_id).all()
        grades_data = []
        
        for grade in grades:
            grades_data.append({
                'student_id': grade.student_id,
                'points': grade.points,
                'percentage': grade.get_percentage(),
                'note_swiss': grade.get_note_swiss()
            })
        
        evaluation_data = {
            'id': evaluation.id,
            'title': evaluation.title,
            'type': evaluation.type,
            'ta_group_name': evaluation.ta_group_name,
            'date': evaluation.date.isoformat() if evaluation.date else None,
            'max_points': evaluation.max_points,
            'min_points': evaluation.min_points,
            'grades': grades_data,
            'average': evaluation.get_average(),
            'grade_distribution': evaluation.get_grade_distribution()
        }
        
        return jsonify({
            'success': True,
            'evaluation': evaluation_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@evaluations_bp.route('/<int:evaluation_id>', methods=['PUT'])
@login_required
def update_evaluation(evaluation_id):
    """Modifier une évaluation"""
    try:
        # Vérifier que l'évaluation appartient à une classe de l'utilisateur
        evaluation = db.session.query(Evaluation).join(
            Classroom, Evaluation.classroom_id == Classroom.id
        ).filter(
            Evaluation.id == evaluation_id,
            Classroom.user_id == current_user.id
        ).first()
        
        if not evaluation:
            return jsonify({'success': False, 'message': 'Évaluation introuvable'}), 404
        
        data = request.get_json()
        
        # Mettre à jour les champs
        if 'title' in data:
            evaluation.title = data['title'].strip()
        
        if 'date' in data:
            try:
                evaluation.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'message': 'Format de date invalide'}), 400
        
        if 'max_points' in data:
            evaluation.max_points = float(data['max_points'])
        
        if 'min_points' in data:
            evaluation.min_points = float(data['min_points'])
        
        # Mettre à jour les notes si fournies
        if 'grades' in data:
            # Supprimer les anciennes notes
            EvaluationGrade.query.filter_by(evaluation_id=evaluation_id).delete()
            
            # Créer les nouvelles notes
            for grade_data in data['grades']:
                student_id = grade_data.get('student_id')
                points = grade_data.get('points')
                
                if student_id and points is not None:
                    grade = EvaluationGrade(
                        evaluation_id=evaluation_id,
                        student_id=student_id,
                        points=float(points)
                    )
                    db.session.add(grade)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Évaluation modifiée avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@evaluations_bp.route('/<int:evaluation_id>', methods=['DELETE'])
@login_required
def delete_evaluation(evaluation_id):
    """Supprimer une évaluation"""
    try:
        # Vérifier que l'évaluation appartient à une classe de l'utilisateur
        evaluation = db.session.query(Evaluation).join(
            Classroom, Evaluation.classroom_id == Classroom.id
        ).filter(
            Evaluation.id == evaluation_id,
            Classroom.user_id == current_user.id
        ).first()
        
        if not evaluation:
            return jsonify({'success': False, 'message': 'Évaluation introuvable'}), 404
        
        # Supprimer l'évaluation (les notes seront supprimées automatiquement via cascade)
        db.session.delete(evaluation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Évaluation supprimée avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500
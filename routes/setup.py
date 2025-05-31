from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models.user import User, Holiday, Break
from models.classroom import Classroom
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField, IntegerField, FieldList, FormField, BooleanField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from datetime import datetime, time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.vaud_holidays import get_vaud_holidays

setup_bp = Blueprint('setup', __name__, url_prefix='/setup')

class ClassroomForm(FlaskForm):
    name = StringField('Nom de la classe', validators=[DataRequired()])
    subject = StringField('Matière enseignée', validators=[DataRequired()])
    color = StringField('Couleur', validators=[DataRequired()], default='#4F46E5')

class HolidayForm(FlaskForm):
    name = StringField('Nom des vacances/congé', validators=[DataRequired()])
    start_date = DateField('Date de début', validators=[DataRequired()])
    end_date = DateField('Date de fin', validators=[DataRequired()])

class BreakForm(FlaskForm):
    name = StringField('Nom de la pause', validators=[DataRequired()])
    start_time = TimeField('Heure de début', validators=[DataRequired()])
    end_time = TimeField('Heure de fin', validators=[DataRequired()])
    is_major_break = BooleanField('Grande pause (pas de pause intercours après)')

class InitialSetupForm(FlaskForm):
    # Année scolaire
    school_year_start = DateField('Début de l\'année scolaire', validators=[DataRequired()])
    school_year_end = DateField('Fin de l\'année scolaire', validators=[DataRequired()])

    # Horaires
    day_start_time = TimeField('Heure de début des cours', validators=[DataRequired()])
    day_end_time = TimeField('Heure de fin des cours', validators=[DataRequired()])
    period_duration = IntegerField('Durée d\'une période (minutes)', validators=[
        DataRequired(),
        NumberRange(min=30, max=120, message="La durée doit être entre 30 et 120 minutes")
    ])
    break_duration = IntegerField('Durée de la pause intercours (minutes)', validators=[
        DataRequired(),
        NumberRange(min=5, max=30, message="La pause doit être entre 5 et 30 minutes")
    ])

    submit = SubmitField('Valider la configuration')

@setup_bp.route('/initial', methods=['GET', 'POST'])
@login_required
def initial_setup():
    form = InitialSetupForm()

    if form.validate_on_submit():
        # Mise à jour des informations utilisateur
        current_user.school_year_start = form.school_year_start.data
        current_user.school_year_end = form.school_year_end.data
        current_user.day_start_time = form.day_start_time.data
        current_user.day_end_time = form.day_end_time.data
        current_user.period_duration = form.period_duration.data
        current_user.break_duration = form.break_duration.data

        try:
            db.session.commit()
            flash('Configuration initiale enregistrée avec succès !', 'success')
            return redirect(url_for('setup.manage_classrooms'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la sauvegarde : {str(e)}', 'error')

    # Pré-remplir si déjà configuré
    if current_user.school_year_start:
        form.school_year_start.data = current_user.school_year_start
        form.school_year_end.data = current_user.school_year_end
        form.day_start_time.data = current_user.day_start_time
        form.day_end_time.data = current_user.day_end_time
        form.period_duration.data = current_user.period_duration
        form.break_duration.data = current_user.break_duration

    return render_template('setup/initial_setup.html', form=form)

@setup_bp.route('/classrooms', methods=['GET', 'POST'])
@login_required
def manage_classrooms():
    if request.method == 'POST':
        # Ajouter une nouvelle classe
        form = ClassroomForm()
        if form.validate_on_submit():
            classroom = Classroom(
                user_id=current_user.id,
                name=form.name.data,
                subject=form.subject.data,
                color=form.color.data
            )
            db.session.add(classroom)
            db.session.commit()
            flash(f'Classe "{classroom.name}" ajoutée avec succès !', 'success')
        return redirect(url_for('setup.manage_classrooms'))

    classrooms = current_user.classrooms.all()
    form = ClassroomForm()
    return render_template('setup/manage_classrooms.html', classrooms=classrooms, form=form)

@setup_bp.route('/classrooms/<int:id>/delete', methods=['POST'])
@login_required
def delete_classroom(id):
    classroom = Classroom.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(classroom)
    db.session.commit()
    flash(f'Classe "{classroom.name}" supprimée avec succès.', 'info')
    return redirect(url_for('setup.manage_classrooms'))

@setup_bp.route('/holidays', methods=['GET', 'POST'])
@login_required
def manage_holidays():
    if request.method == 'POST':
        form = HolidayForm()
        if form.validate_on_submit():
            holiday = Holiday(
                user_id=current_user.id,
                name=form.name.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data
            )
            db.session.add(holiday)
            db.session.commit()
            flash(f'Période de vacances "{holiday.name}" ajoutée avec succès !', 'success')
        return redirect(url_for('setup.manage_holidays'))

    holidays = current_user.holidays.all()
    form = HolidayForm()
    return render_template('setup/manage_holidays.html', holidays=holidays, form=form)

@setup_bp.route('/holidays/<int:id>/delete', methods=['POST'])
@login_required
def delete_holiday(id):
    holiday = Holiday.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(holiday)
    db.session.commit()
    flash(f'Période de vacances "{holiday.name}" supprimée avec succès.', 'info')
    return redirect(url_for('setup.manage_holidays'))

@setup_bp.route('/breaks', methods=['GET', 'POST'])
@login_required
def manage_breaks():
    if request.method == 'POST':
        form = BreakForm()
        if form.validate_on_submit():
            break_obj = Break(
                user_id=current_user.id,
                name=form.name.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
                is_major_break=form.is_major_break.data
            )
            db.session.add(break_obj)
            db.session.commit()
            flash(f'Pause "{break_obj.name}" ajoutée avec succès !', 'success')
        return redirect(url_for('setup.manage_breaks'))

    breaks = current_user.breaks.all()
    form = BreakForm()
    return render_template('setup/manage_breaks.html', breaks=breaks, form=form)

@setup_bp.route('/holidays/import_vaud', methods=['POST'])
@login_required
def import_vaud_holidays():
    """Importe automatiquement les vacances scolaires vaudoises"""
    if not current_user.school_year_start:
        flash('Veuillez d\'abord configurer l\'année scolaire.', 'warning')
        return redirect(url_for('setup.initial_setup'))

    # Récupérer les vacances pour l'année scolaire
    holidays = get_vaud_holidays(current_user.school_year_start)

    if not holidays:
        flash('Aucune donnée de vacances disponible pour cette année scolaire.', 'warning')
        return redirect(url_for('setup.manage_holidays'))

    # Supprimer les anciennes vacances si demandé
    if request.form.get('replace_existing') == 'true':
        Holiday.query.filter_by(user_id=current_user.id).delete()

    # Ajouter les nouvelles vacances
    for holiday_data in holidays:
        # Vérifier si cette période existe déjà
        existing = Holiday.query.filter_by(
            user_id=current_user.id,
            name=holiday_data['name'],
            start_date=holiday_data['start']
        ).first()

        if not existing:
            holiday = Holiday(
                user_id=current_user.id,
                name=holiday_data['name'],
                start_date=holiday_data['start'],
                end_date=holiday_data['end']
            )
            db.session.add(holiday)

    try:
        db.session.commit()
        flash(f'{len(holidays)} périodes de vacances importées avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'import : {str(e)}', 'error')

    return redirect(url_for('setup.manage_holidays'))

@setup_bp.route('/validate_setup', methods=['POST'])
@login_required
def validate_setup():
    """Valide que la configuration de base est complète"""
    # Vérifier que toutes les informations de base sont présentes
    if not current_user.school_year_start or not current_user.day_start_time:
        flash('Veuillez compléter la configuration initiale.', 'warning')
        return redirect(url_for('setup.initial_setup'))

    if current_user.classrooms.count() == 0:
        flash('Veuillez ajouter au moins une classe.', 'warning')
        return redirect(url_for('setup.manage_classrooms'))

    # Marquer la configuration de base comme complète
    current_user.setup_completed = True
    db.session.commit()

    flash('Configuration de base validée ! Créez maintenant votre horaire type.', 'success')
    return redirect(url_for('schedule.weekly_schedule'))

@setup_bp.route('/breaks/<int:id>/delete', methods=['POST'])
@login_required
def delete_break(id):
    break_obj = Break.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(break_obj)
    db.session.commit()
    flash(f'Pause "{break_obj.name}" supprimée avec succès.', 'info')
    return redirect(url_for('setup.manage_breaks'))

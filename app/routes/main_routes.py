import os
from flask import Blueprint, current_app, render_template, flash, redirect, url_for, session, request
from flask_login import login_required, current_user
from app.services.sentiment_analysis import load_sentiment_model

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
        
    # Redirect ke halaman input-data
    return redirect(url_for('main.input_data'))

@main_bp.route('/input-data')
@login_required
def input_data():
    # Cek apakah model terlatih ada
    model_path = current_app.config['MODEL_PATH']
    if not os.path.exists(model_path):
        flash("PERINGATAN: Model terlatih tidak ditemukan di path models/indobert_sentiment_best.pt. Aplikasi mungkin tidak berfungsi dengan benar.", "warning")
    
    # Clear any previous analysis from session
    if 'analysis_file' in session:
        session.pop('analysis_file')
    if 'analysis_context' in session:
        session.pop('analysis_context')
    
    return render_template('input_data.html')

@main_bp.route('/hasil-analisis')
@login_required
def hasil_analisis():
    # Cek apakah ada data analisis
    if 'analysis_file' not in session or 'analysis_context' not in session:
        flash("Tidak ada data analisis. Silakan unggah dan analisis data terlebih dahulu.", "warning")
        return redirect(url_for('main.input_data'))
    
    return render_template('hasil_analisis.html')

@main_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')
import os
from flask import Blueprint, current_app, render_template, flash, redirect, url_for
from app.services.sentiment_analysis import load_sentiment_model

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Cek apakah model terlatih ada
    model_path = current_app.config['MODEL_PATH']
    if not os.path.exists(model_path):
        flash("PERINGATAN: Model terlatih tidak ditemukan di path models/indobert_sentiment_best.pt. Aplikasi mungkin tidak berfungsi dengan benar.", "warning")
    return render_template('index.html')
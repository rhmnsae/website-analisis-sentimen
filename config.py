import os
from datetime import timedelta

class Config:
    SECRET_KEY = 'analisis_sentimen_X'
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MODEL_FOLDER = os.path.join(os.getcwd(), 'models')
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_sessions')
    SESSION_PERMANENT = True  # Ubah menjadi True
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)  # Tambahkan batas waktu session 30 hari
    SESSION_USE_SIGNER = True
    MODEL_PATH = os.path.join(MODEL_FOLDER, 'model-indobert-mgb.pt')
    GEMINI_API_KEY = "AIzaSyCYPhQCDxpyz_MmR86v43XgKvMryx5FfQY"
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.getcwd(), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
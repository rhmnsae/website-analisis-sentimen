import os
import nltk

def download_nltk_resources():
    """Download all necessary NLTK resources"""
    try:
        # Download essential NLTK packages
        nltk.download('stopwords')
        nltk.download('punkt')
        print("NLTK resources downloaded successfully")
    except Exception as e:
        print(f"Error downloading NLTK resources: {e}")

def ensure_directories_exist(app):
    """Ensure all required directories exist"""
    directories = [
        app.config['UPLOAD_FOLDER'],
        app.config['MODEL_FOLDER'],
        app.config['SESSION_FILE_DIR']
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
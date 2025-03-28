import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Gunakan environment variable untuk menentukan mode debug
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Jalankan aplikasi
    app.run(
        host=os.environ.get('FLASK_HOST', '0.0.0.0'),
        port=int(os.environ.get('FLASK_PORT', 5000)),
        debug=debug_mode
    )
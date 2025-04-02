from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import pytz

db = SQLAlchemy()

# Definisi zona waktu Indonesia (WIB, WITA, atau WIT)
INDONESIA_TZ = pytz.timezone('Asia/Jakarta')  # WIB (GMT+7)
# Untuk WITA gunakan: pytz.timezone('Asia/Makassar')
# Untuk WIT gunakan: pytz.timezone('Asia/Jayapura')

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    analyses = db.relationship('Analysis', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Analysis(db.Model):
    __tablename__ = 'analyses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    total_tweets = db.Column(db.Integer, nullable=False)
    positive_count = db.Column(db.Integer, nullable=False)
    neutral_count = db.Column(db.Integer, nullable=False)
    negative_count = db.Column(db.Integer, nullable=False)
    positive_percent = db.Column(db.Float, nullable=False)
    neutral_percent = db.Column(db.Float, nullable=False)
    negative_percent = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data = db.relationship('AnalysisData', backref='analysis', uselist=False, lazy=True)

    @property
    def created_at_local(self):
        """Mengembalikan waktu dalam zona waktu Indonesia."""
        return self.created_at.replace(tzinfo=pytz.utc).astimezone(INDONESIA_TZ)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'total_tweets': self.total_tweets,
            'positive_count': self.positive_count,
            'neutral_count': self.neutral_count,
            'negative_count': self.negative_count,
            'positive_percent': self.positive_percent,
            'neutral_percent': self.neutral_percent,
            'negative_percent': self.negative_percent,
            'created_at': self.created_at_local.strftime('%d %B %Y, %H:%M WIB')
        }
    
    def __repr__(self):
        return f'<Analysis {self.title}>'

class AnalysisData(db.Model):
    __tablename__ = 'analysis_data'
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analyses.id'), nullable=False)
    data_json = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    
    def get_data(self):
        return json.loads(self.data_json)
    
    def set_data(self, data):
        self.data_json = json.dumps(data)
    
    def __repr__(self):
        return f'<AnalysisData for analysis {self.analysis_id}>'

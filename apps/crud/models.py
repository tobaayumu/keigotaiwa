from apps.app import db, login_manager
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, index=True)
    email = db.Column(db.String, unique=True, index=True)
    password_hash = db.Column(db.String)
    boss_id = db.Column(db.Integer, db.ForeignKey("bosses.id"))
    prompt = db.Column(db.String)

    @property
    def password(self):
        raise AttributeError("読み取り不可")
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_dupulicate_email(self):
        return User.query.filter_by(email=self.email).first() is not None

class Boss(db.Model):
    __tablename__ = "bosses"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    personality = db.Column(db.String)
    background = db.Column(db.String)

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'model'
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, role, text):
        self.user_id = user_id
        self.role = role
        self.text = text

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

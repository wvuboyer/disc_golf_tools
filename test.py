from flask_sqlalchemy import SQLAlchemy
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db' 
db = SQLAlchemy(app) 

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    lanes = db.Column(db.Integer, nullable=False)  # Number of lanes
    current_round = db.Column(db.Integer, default=0) 
    players = db.relationship('Player', backref='tournament', lazy=True)
    matches = db.relationship('Match', backref='tournament', lazy=True)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)  # For Swiss pairing

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    round = db.Column(db.Integer, nullable=False)
    player1_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    player1_score = db.Column(db.Integer, default=0)  # Individual match score
    player2_score = db.Column(db.Integer, default=0)  # Individual match score
    lane = db.Column(db.Integer, nullable=True)  # Lane assignment

db.create_all()
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Tournament(db.Model):
    __tablename__ = 'tournament'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    lanes = db.Column(db.Integer, nullable=False)
    bracket_generated = db.Column(db.Boolean, default=False)
    session_uuid = db.Column(db.String(36), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    format = db.Column(db.String(20), nullable=False)


class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)


class Match(db.Model):
    __tablename__ = 'match'
    id = db.Column(db.Integer, primary_key=True)
    player1_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    lane = db.Column(db.Integer, nullable=True)
    result = db.Column(db.String(10), nullable=True)

    player1 = db.relationship('Player', foreign_keys=[player1_id])
    player2 = db.relationship('Player', foreign_keys=[player2_id])


class SwissTournament(db.Model):
    __tablename__ = 'swiss_tournament'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    lanes = db.Column(db.Integer, nullable=False)
    current_round = db.Column(db.Integer, default=0)
    players = db.relationship('SwissPlayer', backref='swiss_tournament', lazy=True)
    matches = db.relationship('SwissMatch', backref='swiss_match', lazy=True)
    session_uuid = db.Column(db.String(36), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)


class SwissPlayer(db.Model):
    __tablename__ = 'swiss_player'
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('swiss_tournament.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)


class SwissMatch(db.Model):
    __tablename__ = 'swiss_match'
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('swiss_tournament.id'), nullable=False)
    round = db.Column(db.Integer, nullable=False)
    player1_id = db.Column(db.Integer, db.ForeignKey('swiss_player.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('swiss_player.id'), nullable=True)  # Make nullable
    player1_score = db.Column(db.Integer, default=0)
    player2_score = db.Column(db.Integer, default=0)
    lane = db.Column(db.Integer, nullable=True)

    player1 = db.relationship('SwissPlayer', foreign_keys=[player1_id])
    player2 = db.relationship('SwissPlayer', foreign_keys=[player2_id])

from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, session
import random

from app import db
from blueprints.putting_league.models import Tournament, Player, Match

putting_league = Blueprint(
    'putting_league',
    __name__,
    url_prefix='/putting_league',
)


@putting_league.route('/')
def index():
    # clean up old tournaments
    cutoff_time = datetime.utcnow() - timedelta(hours=48)
    old_tournaments = Tournament.query.filter(Tournament.created_at < cutoff_time).all()
    for tournament in old_tournaments:
        db.session.delete(tournament)
    db.session.commit()

    tournaments = Tournament.query.filter_by(session_uuid=session['uuid']).all()
    return render_template('putting_league/index.html', tournaments=tournaments)


@putting_league.route('/tournament/create', methods=['GET', 'POST'])
def create_tournament():
    if request.method == 'POST':
        name = request.form['name']
        lanes = int(request.form['lanes'])
        tournament = Tournament(name=name, lanes=lanes, session_uuid=session['uuid'])
        db.session.add(tournament)
        db.session.commit()
        return redirect(url_for('putting_league.index'))
    return render_template('putting_league/create_tournament.html')


@putting_league.route('/tournament/<int:tournament_id>')
def view_tournament(tournament_id):
    tournament = Tournament.query.filter_by(id=tournament_id, session_uuid=session['uuid']).first_or_404()
    players = Player.query.filter_by(tournament_id=tournament_id).all()
    return render_template('putting_league/view_tournament.html', tournament=tournament, players=players)


@putting_league.route('/tournament/<int:tournament_id>/add_player', methods=['POST'])
def add_player(tournament_id):
    tournament = Tournament.query.filter_by(id=tournament_id, session_uuid=session['uuid']).first_or_404()
    if tournament.bracket_generated:
        return "Cannot add players after the bracket is generated.", 400

    name = request.form['name']
    player = Player(name=name, tournament_id=tournament_id)
    db.session.add(player)
    db.session.commit()
    return redirect(url_for('putting_league.view_tournament', tournament_id=tournament_id))


@putting_league.route('/tournament/<int:tournament_id>/remove_player/<int:player_id>')
def remove_player(tournament_id, player_id):
    tournament = Tournament.query.filter_by(id=tournament_id, session_uuid=session['uuid']).first_or_404()
    if tournament.bracket_generated:
        return "Cannot remove players after the bracket is generated.", 400

    player = Player.query.get_or_404(player_id)
    db.session.delete(player)
    db.session.commit()
    return redirect(url_for('putting_league.view_tournament', tournament_id=tournament_id))


@putting_league.route('/tournament/<int:tournament_id>/generate_bracket')
def generate_bracket(tournament_id):
    tournament = Tournament.query.filter_by(id=tournament_id, session_uuid=session['uuid']).first_or_404()
    if tournament.bracket_generated:
        return "Bracket already generated.", 400

    players = Player.query.filter_by(tournament_id=tournament_id).all()
    matchups = []

    for i, player1 in enumerate(players):
        for player2 in players[i+1:]:
            matchups.append((player1, player2))

    random.shuffle(matchups)
    for idx, (player1, player2) in enumerate(matchups):
        match = Match(
            player1_id=player1.id,
            player2_id=player2.id,
            tournament_id=tournament_id,
            lane=(idx % tournament.lanes) + 1
        )
        db.session.add(match)

    tournament.bracket_generated = True
    db.session.commit()
    return redirect(url_for('putting_league.view_tournament', tournament_id=tournament_id))


@putting_league.route('/tournament/<int:tournament_id>/matches')
def view_matches(tournament_id):
    matches = Match.query.filter_by(tournament_id=tournament_id).all()

    all_matches_complete = all(match.result is not None for match in matches)

    return render_template(
        'putting_league/matches.html',
        matches=matches,
        tournament_id=tournament_id,
        all_matches_complete=all_matches_complete
    )


@putting_league.route('/match/<int:match_id>/update', methods=['POST'])
def update_match(match_id):
    match = Match.query.get_or_404(match_id)
    match.result = request.form['result']
    db.session.commit()
    return redirect(url_for('putting_league.view_matches', tournament_id=match.tournament_id))


@putting_league.route('/tournament/<int:tournament_id>/results')
def calculate_results(tournament_id):
    players = Player.query.filter_by(tournament_id=tournament_id).all()
    matches = Match.query.filter_by(tournament_id=tournament_id).all()

    scores = {player.id: 0 for player in players}
    records = {player.id: {"wins": 0, "losses": 0, "ties": 0} for player in players}

    for match in matches:
        if match.result == 'win1':
            scores[match.player1_id] += 2
            records[match.player1_id]["wins"] += 1
            records[match.player2_id]["losses"] += 1
        elif match.result == 'win2':
            scores[match.player2_id] += 2
            records[match.player2_id]["wins"] += 1
            records[match.player1_id]["losses"] += 1
        elif match.result == 'tie':
            scores[match.player1_id] += 1
            scores[match.player2_id] += 1
            records[match.player1_id]["ties"] += 1
            records[match.player2_id]["ties"] += 1

    sorted_scores = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    results = [
        {
            "name": Player.query.get(player_id).name,
            "score": score,
            "record": f"{records[player_id]['wins']}-{records[player_id]['losses']}-{records[player_id]['ties']}"
        }
        for player_id, score in sorted_scores
    ]

    return render_template('putting_league/results.html', results=results)

@putting_league.route('/delete_all')
def delete_all_tournaments():
    tournaments = Tournament.query.filter_by(session_uuid=session['uuid']).all()
    for tournament in tournaments:
        db.session.delete(tournament)
    db.session.commit()
    return redirect(url_for('putting_league.index'))

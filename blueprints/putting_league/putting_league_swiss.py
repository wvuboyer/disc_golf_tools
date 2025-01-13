from datetime import datetime, timedelta
import random
import math

from flask import Blueprint, render_template, redirect, url_for, request, session, flash

from app import db
from blueprints.putting_league.models import (
    SwissTournament as Tournament,
    SwissPlayer as Player,
    SwissMatch as Match
)

MAX_TOURNAMENTS = 10024
MAX_TOURNAMENT_AGE_HOURS = 24
MAX_TOURNAMENTS_PER_SESSION = 12
MAX_UNSTARTED_TOURNAMENT_AGE_HOURS = 1


putting_league_swiss = Blueprint(
    'putting_league_swiss',
    __name__,
    url_prefix='/putting_league_swiss',
)


@putting_league_swiss.route('/')
def index():
    cleanup_old_tournaments()
    tournaments = Tournament.query.filter_by(session_uuid=session['uuid']).all()
    return render_template('putting_league_swiss/index.html', tournaments=tournaments)


@putting_league_swiss.route('/create', methods=['GET', 'POST'])
def create_tournament():
    tournament_count = Tournament.query.count()
    if tournament_count >= MAX_TOURNAMENTS:
        flash('Maximum number of tournaments reached. Please wait for old tournaments to expire.', 'error')
        return redirect(url_for('putting_league_swiss.index'))

    session_tournament_count = Tournament.query.filter_by(session_uuid=session['uuid']).count()
    if session_tournament_count >= MAX_TOURNAMENTS_PER_SESSION:
        flash('Maximum number of tournaments per session reached. Please delete some tournaments.', 'error')
        return redirect(url_for('putting_league_swiss.index'))

    if request.method == 'POST':
        name = request.form['name']
        lanes = int(request.form['lanes'])
        tournament = Tournament(name=name, lanes=lanes, session_uuid=session['uuid'])
        db.session.add(tournament)
        db.session.commit()
        return redirect(url_for('putting_league_swiss.add_players', tournament_id=tournament.id))
    return render_template('putting_league_swiss/create.html')


def cleanup_old_tournaments():
    """Delete tournaments based on age rules:
    - All tournaments older than 24 hours
    - Unstarted tournaments older than 4 hours"""

    cutoff_time = datetime.utcnow() - timedelta(hours=MAX_TOURNAMENT_AGE_HOURS)
    old_tournaments = Tournament.query.filter(Tournament.created_at < cutoff_time).all()

    unstarted_cutoff = datetime.utcnow() - timedelta(hours=MAX_UNSTARTED_TOURNAMENT_AGE_HOURS)
    old_unstarted = Tournament.query.filter(
        Tournament.created_at < unstarted_cutoff,
        Tournament.started == False
    ).all()

    tournaments_to_delete = list(set(old_tournaments + old_unstarted))

    for tournament in tournaments_to_delete:
        Match.query.filter_by(tournament_id=tournament.id).delete()
        Player.query.filter_by(tournament_id=tournament.id).delete()
        db.session.delete(tournament)

    db.session.commit()


@putting_league_swiss.route('/add_players/<string:tournament_id>', methods=['GET', 'POST'])
def add_players(tournament_id):
    if tournament_id is None:
        return redirect(url_for('putting_league_swiss.create_tournament'))

    tournament = Tournament.query.get(tournament_id)
    if tournament.session_uuid != session['uuid']:
        return redirect(url_for('putting_league_swiss.index'))

    if tournament.started:
        return redirect(url_for('putting_league_swiss.start_tournament', tournament_id=tournament.id))

    players = Player.query.filter_by(tournament_id=tournament.id).all()

    if request.method == 'POST':
        if len(players) >= 64:
            flash('Tournament is full - maximum 64 players allowed', 'error')
            return redirect(url_for('putting_league_swiss.add_players', tournament_id=tournament.id))

        name = request.form['name']
        player = Player(name=name, tournament_id=tournament.id)
        db.session.add(player)
        db.session.commit()
        return redirect(url_for('putting_league_swiss.add_players', tournament_id=tournament.id))

    return render_template(
        'putting_league_swiss/add_players.html',
        tournament=tournament,
        players=players,
        spots_remaining=64-len(players)
    )


@putting_league_swiss.route('/start/<string:tournament_id>', methods=["GET"])
def start_tournament(tournament_id):
    if tournament_id is None:
        return redirect(url_for('putting_league_swiss.create_tournament'))

    tournament = Tournament.query.get(tournament_id)
    if tournament.session_uuid != session['uuid']:
        return redirect(url_for('putting_league_swiss.index'))

    if tournament.completed:
        return redirect(url_for('putting_league_swiss.results', tournament_id=tournament.id))

    if tournament.started:
        return redirect(url_for('putting_league_swiss.enter_scores', tournament_id=tournament.id))

    if tournament.current_round == 0:
        tournament.current_round = 1
        db.session.commit()

        generate_pairings(tournament, tournament.players)
        tournament.started = True
        db.session.commit()

    return redirect(url_for('putting_league_swiss.enter_scores', tournament_id=tournament.id))


def generate_pairings(tournament, players):
    """Generate pairings for the current round using Swiss system"""
    if tournament.current_round == 1:
        random.shuffle(players)
        for i in range(0, len(players) - 1, 2):
            if i + 1 < len(players):
                create_match(tournament, players[i], players[i + 1], i // 2)
        if len(players) % 2:
            create_match(tournament, players[-1], None, (len(players) - 1) // 2)
        return

    score_groups = {}
    for player in players:
        score_groups.setdefault(player.score, []).append(player)

    sorted_scores = sorted(score_groups.keys(), reverse=True)
    paired_players = set()
    match_count = 0
    unpaired = []

    for score in sorted_scores:
        group = score_groups[score]
        random.shuffle(group)

        group.extend(unpaired)
        unpaired = []

        group = [p for p in group if p.id not in paired_players]

        while len(group) > 1:
            player1 = group.pop(0)
            for i, player2 in enumerate(group):
                if not has_played_before(player1, player2, tournament.id):
                    paired_players.add(player1.id)
                    paired_players.add(player2.id)
                    create_match(tournament, player1, player2, match_count)
                    match_count += 1
                    group.pop(i)
                    break
            else:
                unpaired.append(player1)

        if group:
            unpaired.extend(group)

    while len(unpaired) > 1:
        player1 = unpaired.pop(0)
        player2 = unpaired.pop(0)
        create_match(tournament, player1, player2, match_count)
        match_count += 1

    if unpaired:
        create_match(tournament, unpaired[0], None, match_count)


def has_played_before(player1, player2, tournament_id):
    """Check if two players have already played against each other"""
    if player2 is None:
        return False

    return Match.query.filter(
        ((Match.player1_id == player1.id) & (Match.player2_id == player2.id)) |
        ((Match.player1_id == player2.id) & (Match.player2_id == player1.id)),
        Match.tournament_id == tournament_id
    ).count() > 0


def create_match(tournament, player1, player2, match_index):
    """Create a match between two players (or bye for single player)"""
    match = Match(
        tournament_id=tournament.id,
        round=tournament.current_round,
        player1_id=player1.id,
        player2_id=player2.id if player2 else None,
        lane=match_index % tournament.lanes + 1
    )
    db.session.add(match)
    db.session.commit()


@putting_league_swiss.route('/enter_scores/<string:tournament_id>', methods=['GET', 'POST'])
def enter_scores(tournament_id):
    if tournament_id is None:
        return redirect(url_for('putting_league_swiss.create_tournament'))

    tournament = Tournament.query.get(tournament_id)
    if tournament.session_uuid != session['uuid']:
        return redirect(url_for('putting_league_swiss.index'))

    if tournament.completed:
        return redirect(url_for('putting_league_swiss.results', tournament_id=tournament.id))

    matches = Match.query.filter_by(tournament_id=tournament.id, round=tournament.current_round).all()

    if request.method == 'POST':
        for match in matches:
            p1_score = int(request.form[f'p1_score_{match.id}'])

            if match.player2_id is None:
                p2_score = 0
            else:
                p2_score = int(request.form[f'p2_score_{match.id}'])

            match.player1_score = p1_score
            match.player2_score = p2_score

            update_player_scores(match, p1_score, p2_score)

        db.session.commit()

        if tournament.current_round == math.ceil(math.log2(len(tournament.players))):
            tournament.completed = True
            db.session.commit()
            return redirect(url_for('putting_league_swiss.results', tournament_id=tournament.id))
        else:
            tournament.current_round += 1
            db.session.commit()

            generate_pairings(tournament, tournament.players)
            db.session.commit()
            return redirect(url_for('putting_league_swiss.enter_scores', tournament_id=tournament.id))

    return render_template(
        'putting_league_swiss/enter_scores.html',
        tournament=tournament,
        matches=matches,
        players={player.id: player.name for player in tournament.players}
    )


def update_player_scores(match, p1_score, p2_score):
    if p1_score > p2_score:
        player = Player.query.get(match.player1_id)
        player.score += 1
    elif p2_score > p1_score:
        player = Player.query.get(match.player2_id)
        player.score += 1
    else:
        player = Player.query.get(match.player1_id)
        player.score += 1
        player2 = Player.query.get(match.player2_id)
        player2.score += 1
    db.session.commit()


@putting_league_swiss.route('/results/<string:tournament_id>')
def results(tournament_id):
    if tournament_id is None:
        flash("Tournament not found!", "error")
        return redirect(url_for('putting_league_swiss.index'))
    tournament = Tournament.query.get(tournament_id)
    if tournament is None:
        flash("Tournament not found!", "error")
        return redirect(url_for('putting_league_swiss.index'))

    if tournament.session_uuid != session['uuid']:
        return redirect(url_for('putting_league_swiss.index'))

    tournament.completed = True
    db.session.commit()

    sorted_players = sorted(tournament.players, key=lambda player: (player.score, player.name))

    total_rounds = tournament.current_round

    results = []
    for tmp, player in enumerate(sorted_players):
        wins = Match.query.filter_by(
            player1_id=player.id, tournament_id=tournament.id
        ).filter(
            Match.player1_score > Match.player2_score
        ).count()
        losses = Match.query.filter_by(
            player1_id=player.id, tournament_id=tournament.id
        ).filter(
            Match.player1_score < Match.player2_score
        ).count()
        ties = Match.query.filter_by(
            player1_id=player.id, tournament_id=tournament.id
        ).filter(
            Match.player1_score == Match.player2_score
        ).count()

        wins += Match.query.filter_by(
            player2_id=player.id, tournament_id=tournament.id
        ).filter(
            Match.player2_score > Match.player1_score
        ).count()
        losses += Match.query.filter_by(
            player2_id=player.id, tournament_id=tournament.id
        ).filter(
            Match.player2_score < Match.player1_score
        ).count()
        ties += Match.query.filter_by(
            player2_id=player.id, tournament_id=tournament.id
        ).filter(
            Match.player2_score == Match.player1_score
        ).count()

        results.append({
            'player': player,
            'wins': wins,
            'losses': losses,
            'ties': ties,
            'score': (wins * 2) + (ties * 1)
        })
        results = sorted(results, key=lambda x: x['score'], reverse=True)

    return render_template(
        'putting_league_swiss/results.html',
        tournament=tournament, results=results, total_rounds=total_rounds
    )


@putting_league_swiss.route('/delete_all')
def delete_all_tournaments():
    tournaments = Tournament.query.filter_by(session_uuid=session['uuid']).all()
    for tournament in tournaments:
        players = Player.query.filter_by(tournament_id=tournament.id).all()
        for player in players:
            db.session.delete(player)
            db.session.commit()
        matches = Match.query.filter_by(tournament_id=tournament.id).all()
        for match in matches:
            db.session.delete(match)
            db.session.commit()
        db.session.delete(tournament)
    db.session.commit()
    return redirect(url_for('putting_league_swiss.index'))

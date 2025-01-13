import uuid
from flask import Flask, session
from blueprints.putting_league.models import db


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.secret_key = uuid.uuid4().hex

    db.init_app(app)
    with app.app_context():
        db.create_all()

    from blueprints.base import base_bp
    from blueprints.player_cards import player_cards_bp
    from blueprints.payout_cards import payout_cards_bp
    from blueprints.payout_cards_pdga import payout_cards_pdga_bp
    from blueprints.putting_league.putting_league import putting_league as putting_league_rr
    from blueprints.putting_league.putting_league_swiss import putting_league_swiss

    app.register_blueprint(base_bp)
    app.register_blueprint(player_cards_bp)
    app.register_blueprint(payout_cards_bp)
    app.register_blueprint(payout_cards_pdga_bp)
    app.register_blueprint(putting_league_rr)
    app.register_blueprint(putting_league_swiss)

    @app.before_request
    def before_request():
        if 'uuid' not in session:
            session['uuid'] = str(uuid.uuid4())

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)

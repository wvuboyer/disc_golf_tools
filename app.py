import uuid
from flask import Flask
from blueprints.base import base_bp
from blueprints.player_cards import player_cards_bp

app = Flask(__name__)
app.secret_key = uuid.uuid4().hex
app.register_blueprint(base_bp)
app.register_blueprint(player_cards_bp)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

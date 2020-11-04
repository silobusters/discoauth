import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import json

load_dotenv()


db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask('discoauth', instance_relative_config=True)
    app.config.from_object('config')
    app.config.from_pyfile('config.py')
    app.secret_key = bytes(os.getenv('SB_FLASK_SECRET_KEY'), 'utf-8').decode('unicode_escape')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SB_DATABASE_URL']

    db.init_app(app)
    migrate = Migrate(app, db)

    from discoauth.oauth.discord_oauth import bp_discord_oauth
    app.register_blueprint(bp_discord_oauth, url_prefix='/auth')

    return app

from discoauth import models


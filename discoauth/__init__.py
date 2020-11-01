import os
from flask import Flask
from dotenv import load_dotenv
from flask_migrate import Migrate
import json

load_dotenv()

from .models import db, AffiliatedGuild, SupportedService
from .oauth.discord_oauth import discord_oauth




app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')
app.secret_key = bytes(os.getenv('SB_FLASK_SECRET_KEY'), 'utf-8').decode('unicode_escape')
app.register_blueprint(discord_oauth, url_prefix='/auth')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SB_DATABASE_URL']
db.init_app(app)

@app.before_first_request
def populate_static_tables():
    if not AffiliatedGuild.query.all():
        with open('discoauth/affiliated_guilds.json', 'r') as f:
            data = json.load(f)
            for entry in data:
                guild = AffiliatedGuild(**entry)
                db.session.add(guild)
            db.session.commit()
    if not SupportedService.query.all():
        with open('discoauth/supported_services.json', 'r') as f:
            data = json.load(f)
            for entry in data:
                service = SupportedService(**entry)
                db.session.add(service)
            db.session.commit()


migrate = Migrate(app, db)

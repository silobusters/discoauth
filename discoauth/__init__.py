import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import json
import requests
from hashlib import sha256

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv('SB_DISCORD_BOT_TOKEN')
DISCORD_API_BASE_URL = os.getenv('SB_DISCORD_API_BASE_URL')

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask('discoauth', instance_relative_config=True)
    app.config.from_object('config')
    app.config.from_pyfile('config.py')
    app.secret_key = bytes(os.getenv('SB_FLASK_SECRET_KEY'), 'utf-8').decode('unicode_escape')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SB_DATABASE_URL']
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///silobusters-dev.db'


    db.init_app(app)
    migrate = Migrate(app, db)

    from discoauth.oauth.discord_oauth import bp_discord_oauth
    app.register_blueprint(bp_discord_oauth, url_prefix='/auth')
    from discoauth.oauth.github_oauth import bp_github_oauth
    app.register_blueprint(bp_github_oauth, url_prefix='/auth')
    from discoauth.integration.api import bp_discoauth_api
    app.register_blueprint(bp_discoauth_api, url_prefix='/api')

    return app

from discoauth import models
from discoauth.models import User, UserOAuth, AffiliatedGuild, ServiceVerification, SupportedService 

app = create_app()
app.app_context().push()

@app.before_first_request
def populate_static_tables():
    print(f"database url: {app.config['SQLALCHEMY_DATABASE_URI']}")
    # try:
    #     print("populating static tables: guild")
    #     AffiliatedGuild.query.all()
#    if not db.session.query(affiliated_guild).first():
    if not AffiliatedGuild.query.all():
#    except:
        headers_payload = {"Authorization":f"Bot {DISCORD_BOT_TOKEN}","User-Agent":"silobusters (http://silobusters.shamacon.us, v0.01)","Content-Type":"application/json"}
        r = requests.get(f'{DISCORD_API_BASE_URL}/users/@me/guilds', headers=headers_payload)
        print('Retrieving guild affiliations...')
        if r.status_code == 200:
            guilds_object = json.loads(r.text)
            if len(guilds_object):
                for guild in guilds_object:
                    entry = {}
                    entry['guild_id'] = guild['id']
                    entry['guild_hash'] = sha256(guild['id'].encode('utf-8')).hexdigest()
                    guild_entry = AffiliatedGuild(**entry)
                    db.session.add(guild_entry)
                db.session.commit()
                AFFILIATED_GUILDS = True
                print("Populated guild list from API")
            else:
                print("Error: guild list is empty") # TODO add logging and error reporting
        else:
            print(f'affilated guild query result: {r.status_code}: {r.text}')
#    try:
#        SupportedService.query.all()
    if not SupportedService.query.all():
#    except:
        with open('discoauth/supported_services.json', 'r') as f:
            data = json.load(f)
            for entry in data:
                service = SupportedService(**entry)
                db.session.add(service)
            db.session.commit()
#    try:
#        ServiceVerification.query.all()
    if not ServiceVerification.query.all():
#    except:
        with open('discoauth/service_verifications.json', 'r') as f:
            data = json.load(f)
            for entry in data:
                verification = ServiceVerification(**entry)
                db.session.add(verification)
            db.session.commit()
            SERVICE_VERIFICATIONS = True

#app.before_request(populate_static_tables) 

import os
from flask import Flask


from .oauth.discord_oauth import discord_oauth




app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')
app.secret_key = bytes(os.getenv('SB_FLASK_SECRET_KEY'), 'utf-8').decode('unicode_escape')
app.register_blueprint(discord_oauth, url_prefix='/auth')

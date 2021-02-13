from flask import Blueprint, request, session, redirect, url_for, jsonify
from requests_oauthlib import OAuth2Session
from hashlib import sha256
import os
import requests
import json
from datetime import datetime as dt

from discoauth import create_app, db
from discoauth.models import User, UserOAuth, AffiliatedGuild, ServiceVerification, SupportedService 

bp_discoauth_api = Blueprint('bp_discoauth_api', __name__)

app = create_app()
app.app_context().push()

@bp_discoauth_api.route('/users/github/<snowflake>')
def get_user(snowflake):
#    known_user = UserOauth.query.filter_by(discord_user_id=str(snowflake)).first()
    known_user = UserOAuth.query.filter_by(
        discord_user_id=str(snowflake),
        service_id=2
        ).first()
    if known_user:
        result = {"discordSnowflake":snowflake, "githubUserId":known_user.service_user_id}
        return jsonify(result)
    return jsonify({"discordSnowflake":snowflake, "githubUserId":None}), 404

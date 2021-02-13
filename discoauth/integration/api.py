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

# This is an ugly way to declare authorized client keys
authorized_apps = []
authorized_apps.append(os.getenv('SB_PROMOBOT_AUTH_KEY'))
authorized_apps.append(os.getenv('SB_ARGENT_AUTH_KEY'))
authorized_apps.append(os.getenv('SB_CDC_AUTH_KEY'))

app = create_app()
app.app_context().push()

@bp_discoauth_api.route('/users/github/<snowflake>')
def get_user(snowflake):
    authorized_request = False
    if "Authorization" in request.headers:
        if request.headers["Authorization"] in authorized_apps:
            authorized_request = True
    if not authorized_request:
        return jsonify({"error":"unauthorized"}), 403

#    known_user = UserOauth.query.filter_by(discord_user_id=str(snowflake)).first()
    known_user = UserOAuth.query.filter_by(discord_user_id=str(snowflake)).all()
    if known_user:
#        result = {"discordSnowflake":snowflake, "githubUserId":known_user.service_user_id}
        result = {}
        result["discordSnowflake"] = snowflake
        for i in known_user:
            result[f"{SupportedService.query.filter_by(service_id=i.service_id).first().service_name.lower()}UserId"] = i.service_user_id
        return jsonify(result)
    return jsonify({"discordSnowflake":snowflake, "githubUserId":None}), 404

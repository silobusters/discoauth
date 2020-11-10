from flask import Blueprint, request, session, redirect, url_for
from requests_oauthlib import OAuth2Session
from hashlib import sha256
import os
import requests
import json
from datetime import datetime as dt

from discoauth import create_app, db
from discoauth.models import User, UserOAuth, AffiliatedGuild, ServiceVerification, SupportedService 

bp_github_oauth = Blueprint('bp_github_oauth', __name__)

app = create_app()
app.app_context().push()


GITHUB_OAUTH2_CLIENT_ID = os.getenv('SB_GITHUB_OAUTH2_CLIENT_ID')
GITHUB_OAUTH2_CLIENT_SECRET = os.getenv('SB_GITHUB_OAUTH2_CLIENT_SECRET')
GITHUB_OAUTH2_REDIRECT_URI = os.getenv('SB_GITHUB_OAUTH2_REDIRECT_URI')

GITHUB_API_BASE_URL = 'https://api.github.com'
GITHUB_AUTHORIZATION_BASE_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'

DISCORD_API_BASE_URL = os.getenv('SB_DISCORD_API_BASE_URL')
DISCORD_AUTHORIZATION_BASE_URL = DISCORD_API_BASE_URL + '/oauth2/authorize'
DISCORD_TOKEN_URL = DISCORD_API_BASE_URL + '/oauth2/token'

DISCORD_BOT_TOKEN = os.getenv('SB_DISCORD_BOT_TOKEN')

HASH_SALT = os.getenv("SB_FLASK_SECRET_KEY")

if 'http://' in GITHUB_OAUTH2_REDIRECT_URI:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

def github_token_updater(token):
    session['oauth2_token'] = token

def make_github_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=GITHUB_OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=GITHUB_OAUTH2_REDIRECT_URI,
        auto_refresh_kwargs={
            'client_id': GITHUB_OAUTH2_CLIENT_ID,
            'client_secret': GITHUB_OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=GITHUB_TOKEN_URL,
        token_updater=github_token_updater)

def in_guild(id, guild=None):
    if guild:
        headers_payload = {"Authorization":f"Bot {DISCORD_BOT_TOKEN}","User-Agent":"silobusters (http://silobusters.shamacon.us, v0.01)","Content-Type":"application/json"}
        r = requests.get(f'{DISCORD_API_BASE_URL}/guilds/{guild}/members/{id}', headers=headers_payload)
        print(f"in_guild request for {id} in {guild} met with response code {r.status_code}")
        print(r.text)
        if r.status_code == 200:
            return True
        return False

def assign_github_verified_role(id, token): #this should cascade to all affiliated guilds with verifications for this service
    data_payload = json.dumps({"access_token":token})
    headers_payload = {"Authorization":f"Bot {DISCORD_BOT_TOKEN}","User-Agent":"silobusters (http://silobusters.shamacon.us, v0.01)","Content-Type":"application/json"}
    response_payload = []
    try:
        AFFILIATED_GUILDS = []
        if AffiliatedGuild.query.all():
            for guild in AffiliatedGuild.query.all():
                print(f'guild is {guild.guild_id}')
                AFFILIATED_GUILDS.append(guild.guild_id)
        else:
            AFFILIATED_GUILDS = False
            print(f'No guilds found.')
            response_payload = [{"Error": "No affiliated guilds registered."}]

        SERVICE_VERIFICATIONS = False
        if ServiceVerification.query.all():
            SERVICE_VERIFICATIONS = True
        else:
            response_payload.append({"Error": "No service verifications registered."})

    except Error as e:
        print("DATABASE IS MISSING INITIAL DATA.", e)

    if AFFILIATED_GUILDS and SERVICE_VERIFICATIONS:
        for guild in AFFILIATED_GUILDS:
            if in_guild(id, guild):
                for verification in ServiceVerification.query.all():
                    if verification.guild_id == guild and verification.service_id == 2:
                        assign_url = f'{DISCORD_API_BASE_URL}/guilds/{guild}/members/{id}/roles/{verification.verified_role_id}'
                        r = requests.put(assign_url, headers=headers_payload, data=data_payload)
                        response_payload.append({"guild": guild, "role": verification.verified_role_id, "status": r.status_code})
                        print(f"Request to add github-verified role to user {id} met with response code {r.status_code}: {r.content}")
    print(response_payload)
    return response_payload

def validate_sb_token(sb_token_hash):
    if sb_token_hash:
        sb_user = User.query.filter_by(sb_verification_token_hash=sb_token_hash).first()
        if sb_user:
            sb_fields = json.loads(sb_user.sb_verification_token)
            if sb_fields['service_name'] == 'GitHub':
                return json.loads(sb_user.sb_verification_token)
            return None
        else:
            return None
    else:
        return None

@bp_github_oauth.route('/github')
def authorize_github(): # TODO devise a way to enumerate and encode github scopes
    sb_token_hash = request.args.get('token', default=None, type=str)
    if not sb_token_hash:
        return "PARAMETER ERROR."
    sb_fields = validate_sb_token(sb_token_hash)
    sb_duid = sb_fields['discord_user_id']
    sb_scope = sb_fields['service_scope']
    github = make_github_session(scope=sb_scope, state=sb_token_hash)
    authorization_url, state = github.authorization_url(GITHUB_AUTHORIZATION_BASE_URL)
    return redirect(authorization_url)

@bp_github_oauth.route('/callback_github')
def callback_github():
    if request.values.get('error'):
        return request.values['error']
    github = make_github_session(state=session.get('oauth2_state'))
    token = github.fetch_token(
        GITHUB_TOKEN_URL,
        client_secret=GITHUB_OAUTH2_CLIENT_SECRET,
        authorization_response=request.url)
    print(f"Callback: GitHub Token is: {token}")
    session['oauth2_token'] = token
    sb_token_hash = request.args.get('state')
    print(sb_token_hash)
    github.headers['Accept'] = 'application/vnd.github.baptiste-preview'
    user = github.get(GITHUB_API_BASE_URL+'/user').json()
    print(f"user:{user['login']} ({user['id']})")
    github_username = user['login']
    github_id = user['id']
    try:
        gh_user = User.query.filter_by(sb_verification_token_hash=sb_token_hash).first()
        gh_user_duid = gh_user.discord_user_id
    except:
        return "ERROR: USER AUTHENTICATED WITH INVALID TOKEN"
    gh_token = session.get('oauth2_token')
    gh_auth = UserOAuth.query.filter_by(discord_user_id=gh_user.discord_user_id, service_id=2).first()
    if gh_auth:
        gh_auth.access_token = gh_token['access_token']
    else:
        new_auth_entry = UserOAuth(discord_user_id=gh_user_duid, service_id=2, service_user_id=user['id'], access_token=gh_token['access_token'], scope=', '.join(gh_token['scope']))
        db.session.add(new_auth_entry)
    db.session.commit()
    db.session.close()
    assign_github_verified_role(gh_user_duid, gh_token['access_token'])
    return redirect(url_for('bp_discord_oauth.confirmation', service=sha256('GitHub'.encode('utf-8')).hexdigest()))



    
#     if join:
#         target_guild = AffiliatedGuild.query.filter_by(guild_id=join).first()
#         if not target_guild:
#             return "404" # TODO choose a more appropriate response for an invalid guild id
#         join = sha256(join.encode('utf-8')).hexdigest()
#         join_param = f'_{join}'
#         scope = request.args.get(
#             'scope',
#             'identify connections guilds.join'
#         )
#         discord = make_discord_session(scope=scope.split(' '))
#         authorization_url, state = discord.authorization_url(DISCORD_AUTHORIZATION_BASE_URL)
# #This is ugly, but I'm using it to avoid registering additional callback URIs with discord
# #Maybe I should be using new_state()
# #I definitely shouldn't be repeating this ugly pattern like I am
#         state_param = state
    #     if link:
    #         link = sha256(link.encode('utf-8')).hexdigest()
    #         link_param = f'-{link}'
    #         discord = make_discord_session(scope=scope.split(' '), state=f'{state_param}_{join}-{link}')
    #     else:
    #         discord = make_discord_session(scope=scope.split(' '), state=f'{state_param}_{join}')
    #     authorization_url, state = discord.authorization_url(DISCORD_AUTHORIZATION_BASE_URL)
    # else:
    #     scope = request.args.get(
    #         'scope',
    #         'identify connections'
    #     )
    #     discord = make_discord_session(scope=scope.split(' '))
    #     authorization_url, state = discord.authorization_url(DISCORD_AUTHORIZATION_BASE_URL)
    #     state_param = state
    #     if link:
    #         link = sha256(link.encode('utf-8')).hexdigest()
    #         link_param = f'-{link}'
    #         discord = make_discord_session(scope=scope.split(' '), state=f'{state_param}-{link}')
    #     else:
    #         discord = make_discord_session(scope=scope.split(' '), state=f'{state_param}')
    #     authorization_url, state = discord.authorization_url(DISCORD_AUTHORIZATION_BASE_URL)
    # print(f'state is {state}')
    # session['oauth2_state'] = state
    # print(f"state is {state}, session is {session['oauth2_state']}")
    # return redirect(authorization_url)
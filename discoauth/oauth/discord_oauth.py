from flask import Blueprint, request, session, redirect, url_for
from flask import current_app as app
from requests_oauthlib import OAuth2Session
from hashlib import sha256
import os

from .models import User, UserOAuth, AffiliatedGuild, ServiceVerification, db

DISCORD_OAUTH2_CLIENT_ID = os.getenv('SB_DISCORD_OAUTH2_CLIENT_ID')
DISCORD_OAUTH2_CLIENT_SECRET = os.getenv('SB_DISCORD_OAUTH2_CLIENT_SECRET')
DISCORD_OAUTH2_REDIRECT_URI = os.getenv('SB_DISCORD_OAUTH2_REDIRECT_URI')

DISCORD_API_BASE_URL = os.getenv('SB_DISCORD_API_BASE_URL')
DISCORD_AUTHORIZATION_BASE_URL = DISCORD_API_BASE_URL + '/oauth2/authorize'
DISCORD_TOKEN_URL = DISCORD_API_BASE_URL + '/oauth2/token'

discord_oauth = Blueprint('discord_oauth', __name__)

if 'http://' in DISCORD_OAUTH2_REDIRECT_URI:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

def discord_token_updater(token):
    discord_session['oauth2_token'] = token

def make_discord_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=DISCORD_OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=DISCORD_OAUTH2_REDIRECT_URI,
        auto_refresh_kwargs={
            'client_id': DISCORD_OAUTH2_CLIENT_ID,
            'client_secret': DISCORD_OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=DISCORD_TOKEN_URL,
        token_updater=discord_token_updater)

@discord_oauth.route('/discord')
def authorize_discord():
    join = request.args.get('guid', default=None, type=str)
    link = request.args.get('link', default=None, type=str)            
    if join:
        join = sha256(join.encode('utf-8')).hexdigest()
        join_param = f'_{join}'
        scope = request.args.get(
            'scope',
            'identify connections guilds.join'
        )
        discord = make_discord_session(scope=scope.split(' '))
        authorization_url, state = discord.authorization_url(DISCORD_AUTHORIZATION_BASE_URL)
#This is ugly, but I'm using it to avoid registering additional callback URIs with discord
#Maybe I should be using new_state()
#I definitely shouldn't be repeating this ugly pattern like I am
        state_param = state
        if link:
            link = sha256(link.encode('utf-8')).hexdigest()
            link_param = f'-{link}'
            discord = make_discord_session(scope=scope.split(' '), state=f'{state_param}_{join}-{link}')
        else:
            discord = make_discord_session(scope=scope.split(' '), state=f'{state_param}_{join}')
        authorization_url, state = discord.authorization_url(DISCORD_AUTHORIZATION_BASE_URL)
    else:
        scope = request.args.get(
            'scope',
            'identify connections'
        )
        discord = make_discord_session(scope=scope.split(' '))
        authorization_url, state = discord.authorization_url(DISCORD_AUTHORIZATION_BASE_URL)
        state_param = state
        if link:
            link = sha256(link.encode('utf-8')).hexdigest()
            link_param = f'-{link}'
            discord = make_discord_session(scope=scope.split(' '), state=f'{state_param}-{link}')
        else:
            discord = make_discord_session(scope=scope.split(' '), state=f'{state_param}')
        authorization_url, state = discord.authorization_url(DISCORD_AUTHORIZATION_BASE_URL)
    print(f'state is {state}')
    session['oauth2_state'] = state
    print(f"state is {state}, session is {session['oauth2_state']}")
    return redirect(authorization_url)

@discord_oauth.route('/callback_discord')
def callback_discord():
    rstate = request.args.get('state', default = None, type = str)
#this "link" value is to support hooking to additional third party services after authentication
    if "-" in rstate:
        link = rstate.split('-')[-1]
        rstate = rstate.split('-', 1)[0]
        if "_" in rstate:
            guid = rstate.split('_')[-1]
        else:
            guid = None
    else:
        link = None
    if "_" in rstate:
        guid = rstate.split('_')[-1]
    else:
        guid = None
    if request.values.get('error'):
        return request.values['error']
    discord = make_discord_session(state=session.get('oauth2_state'))
    token = discord.fetch_token(
        DISCORD_TOKEN_URL,
        client_secret=DISCORD_OAUTH2_CLIENT_SECRET,
        authorization_response=request.url)
    session['oauth2_token'] = token
#    i have a token now and i should be storing it
#    I should also be making my checks for guild membership in case i need to elevate discord permissions after this
#    This also means i need to make a parameter to indicate elevated permission is required -- or enumerate it in the service parameters
    return redirect(url_for('.confirmation', service=sha256('Discord'.encode('utf-8')).hexdigest(), guid=guid, link=link))

@discord_oauth.route('/confirmation')
def confirmation(): # Take link value and compare it to hashes of active integration routes, then redirect to first match
    service = request.args.get('service', default=None, type=str)
    guid = request.args.get('guid', default=None, type=str)
    link = request.args.get('link', default=None, type=str)
### exploring
    for rule in current_app.url_map.iter_rules():
        if "GET" in rule.methods and rule.endpoint != "static":
            print(url_for(rule.endpoint))

    discord = make_discord_session(token=session.get('oauth2_token'))
    user  = discord.get(f"{DISCORD_API_BASE_URL}/users/@me").json()
    known_user = User.filter_by(discord_user_id=user['id'])
    if known_user:
        print(session.get('oauth2_token'))
    else:
        print(f"New user: {session.get('oauth2_token')}")

    return f"ayyyy lmao your service is {service}, your link is {link} and your guid is {guid}"

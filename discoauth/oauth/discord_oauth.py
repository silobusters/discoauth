from flask import Blueprint, request, session, redirect, url_for
from requests_oauthlib import OAuth2Session
from hashlib import sha256
import os
import requests
import json

from discoauth import create_app, db
from discoauth.models import User, UserOAuth, AffiliatedGuild, ServiceVerification, SupportedService 

bp_discord_oauth = Blueprint('bp_discord_oauth', __name__)

app = create_app()
app.app_context().push()

#db.create_all()

DISCORD_OAUTH2_CLIENT_ID = os.getenv('SB_DISCORD_OAUTH2_CLIENT_ID')
DISCORD_OAUTH2_CLIENT_SECRET = os.getenv('SB_DISCORD_OAUTH2_CLIENT_SECRET')
DISCORD_OAUTH2_REDIRECT_URI = os.getenv('SB_DISCORD_OAUTH2_REDIRECT_URI')

DISCORD_API_BASE_URL = os.getenv('SB_DISCORD_API_BASE_URL')
DISCORD_AUTHORIZATION_BASE_URL = DISCORD_API_BASE_URL + '/oauth2/authorize'
DISCORD_TOKEN_URL = DISCORD_API_BASE_URL + '/oauth2/token'

DISCORD_BOT_TOKEN = os.getenv('SB_DISCORD_BOT_TOKEN')
DISCORD_API_BASE_URL = os.getenv('SB_DISCORD_API_BASE_URL')



AFFILIATED_GUILDS = False
# if AffiliatedGuild.query.all():
#     for guild in AffiliatedGuild.query.all():
#         AFFILIATED_GUILDS.append(guild.guild_id)

SERVICE_VERIFICATIONS = False
# if ServiceVerification.query.all():
#     SERVICE_VERIFICATIONS = True

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

def in_guild(id, guild):
    headers_payload = {"Authorization":f"Bot {DISCORD_BOT_TOKEN}","User-Agent":"silobusters (http://silobusters.shamacon.us, v0.01)","Content-Type":"application/json"}
    r = requests.get(f'{DISCORD_API_BASE_URL}/guilds/{guild}/members/{id}', headers=headers_payload)
    print(f"in_guild request for {id} in {guild} met with response code {r.status_code}")
    return r.status_code

def get_affiliated_guilds(): # Don't worry about pagination yet
    headers_payload = {"Authorization":f"Bot {DISCORD_BOT_TOKEN}","User-Agent":"silobusters (http://silobusters.shamacon.us, v0.01)","Content-Type":"application/json"}
    r = requests.get(f'{DISCORD_API_BASE_URL}/users/@me/guilds')
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
            return r.status_code
        else:
            return "Error: guild list is empty" # TODO add logging and error reporting
    else:
        return r.status_code

def join_affiliated_guild(id, guild, token):
    data_payload = json.dumps({"access_token":token})
    headers_payload = {"Authorization":f"Bot {DISCORD_BOT_TOKEN}","User-Agent":"silobusters (http://silobusters.shamacon.us, v0.01)","Content-Type":"application/json"}
    join_url = f'{DISCORD_API_BASE_URL}/guilds/{guild}/members/{id}'
    r = requests.put(join_url, headers=headers_payload, data=data_payload)
    print(f"Request to add user {id} to guild {guild} met with response code {r.status_code}")
    return r.status_code

# THIS DOES NOT BELONG HERE
def assign_github_verified_role(id, github_username, token): #this should cascade to all affiliated guilds with verifications for this service
    data_payload = json.dumps({"access_token":token})
    headers_payload = {"Authorization":f"Bot {DISCORD_BOT_TOKEN}","User-Agent":"silobusters (http://silobusters.shamacon.us, v0.01)","Content-Type":"application/json"}
    response_payload = []
    if AFFILIATED_GUILDS and SERVICE_VERIFICATIONS:
        for guild in AFFILIATED_GUILDS:
            if in_guild(id, guild.guild_id) == 200:
                for verification in ServiceVerification.query.all():
                    if verification.guild_id == guild.guild_id and verification.service_id == 2:
                        assign_url = f'{DISCORD_API_BASE_URL}/guilds/{guild.guild_id}/members/{id}/roles/{verification.verified_role_id}'
                        r = requests.put(assign_url, headers=headers_payload, data=data_payload)
                        response_payload.append({"guild": guild.guild_id, "role": verification.verified_role_id, "status": r.status_code})
                        print(f"Request to add github-verified role to user {id} met with response code {r.status_code}: {r.content}")
    elif SERVICE_VERIFICATIONS:
        response_payload = [{"Error": "No affiliated guilds registered."}]
    else:
        response_payload.append({"Error": "No service verifications registered."})
    print(response_payload)
    return response_payload

@bp_discord_oauth.route('/discord')
def authorize_discord():
    join = request.args.get('guid', default=None, type=str)
    link = request.args.get('link', default=None, type=str)            
    if join:
        target_guild = AffiliatedGuild.query.filter_by(guild_id=join).first()
        if not target_guild:
            return "404" # TODO choose a more appropriate response for an invalid guild id
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

@bp_discord_oauth.route('/callback_discord')
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

@bp_discord_oauth.route('/confirmation')
def confirmation(): # Take link value and compare it to hashes of active integration routes, then redirect to first match
    service = request.args.get('service', default=None, type=str)
    guid = request.args.get('guid', default=None, type=str)
    link = request.args.get('link', default=None, type=str)
## exploring
    print("showing routes")
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and rule.endpoint != "static":
            print(url_for(rule.endpoint))

    discord = make_discord_session(token=session.get('oauth2_token'))
    user  = discord.get(f"{DISCORD_API_BASE_URL}/users/@me").json()
    new_token = session.get('oauth2_token')
    new_user_entry = User(discord_user_id=user['id'])
    new_user_oauth_entry = UserOAuth(discord_user_id=user['id'], service_id=1, service_user_id=user['id'], token=new_token['access_token'], scope=', '.join(new_token['scope']))
    known_user = User.query.filter_by(discord_user_id=user['id']).first()
    if not known_user:
        print(f"New user: {user['id']} - {user['username']}")
        db.session.add(new_user_entry)
        db.session.add(new_user_oauth_entry)
        db.session.commit()
        db.session.close()

    return f"ayyyy lmao your service is {service}, your link is {link} and your guid is {guid}"

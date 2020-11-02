from flask import Blueprint
from flask import current_app as app
import requests
import os
import json

from ..models import db, AffiliatedGuild, ServiceVerification


DISCORD_BOT_TOKEN = os.getenv('SB_DISCORD_BOT_TOKEN')
DISCORD_API_BASE_URL = os.getenv('SB_DISCORD_API_BASE_URL')

AFFILIATED_GUILDS = []
if AffiliatedGuild.query.all():
    for guild in AffiliatedGuild.query.all():
        AFFILIATED_GUILDS.append(guild.guild_id)

SERVICE_VERIFICATIONS = False
if ServiceVerification.query.all():
    SERVICE_VERIFICATIONS = True

discord_user = Blueprint('discord_user', __name__)


def in_guild(id, guild):
    headers_payload = {"Authorization":f"Bot {DISCORD_BOT_TOKEN}","User-Agent":"silobusters (http://silobusters.shamacon.us, v0.01)","Content-Type":"application/json"}
    r = requests.get(f'{DISCORD_API_BASE_URL}/guilds/{guild}/members/{id}', headers=headers_payload)
    print(f"in_guild request for {id} in {guild} met with response code {r.status_code}")
    return r.status_code

def join_affiliated_guild(id, guild, token):
    data_payload = json.dumps({"access_token":token})
    headers_payload = {"Authorization":f"Bot {DISCORD_BOT_TOKEN}","User-Agent":"silobusters (http://silobusters.shamacon.us, v0.01)","Content-Type":"application/json"}
    join_url = f'{DISCORD_API_BASE_URL}/guilds/{guild}/members/{id}'
    r = requests.put(join_url, headers=headers_payload, data=data_payload)
    print(f"Request to add user {id} to guild {guild} met with response code {r.status_code}")
    return r.status_code

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


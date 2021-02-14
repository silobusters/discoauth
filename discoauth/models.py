from discoauth import db
from datetime import datetime as dt

class User(db.Model):
    __tablename__ = 'user'

    discord_user_id = db.Column(db.String, primary_key=True)
    discord_user_id_hash = db.Column(db.String) # we're not using this and I don't think it saves us much time to pre-hash
    github_event_announce = db.Column(db.Boolean, default=True)
    github_entity_reaction = db.Column(db.Boolean, default=True)
    github_gist_append_url = db.Column(db.String) # target gist to append emoji-reacted messages
    stackexchange_assistant_opt_in = db.Column(db.Boolean, default=False)
    stackexchange_assistant_topics = db.Column(db.String) # some array of topics/tags/whatever to monitor
    stackexchange_publisher_opt_in = db.Column(db.Boolean, default=True)
    sb_verification_token = db.Column(db.String) # Token to use in sessions between two services ("discord_user_id", "service_name", [scope])
    sb_verification_token_hash = db.Column(db.String) # is there a reason to pre-hash this?
    sb_status_id = db.Column(db.Integer, default=1)
    creation_date = db.Column(db.DateTime, default=dt.utcnow)
    last_updated = db.Column(db.DateTime, onupdate=dt.utcnow)
    authorization_grants = db.relationship('UserOAuth', backref='user', lazy=True)
    guild_authorizations = db.relationship('AffiliatedGuild', backref='authority', lazy=True)

class SupportedService(db.Model):
    __tablename__ = 'supported_service'

    service_id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String)
    service_hash = db.Column(db.String)
    authorization_grants = db.relationship('UserOAuth', backref='service', lazy=True)
    guild_verifications = db.relationship('ServiceVerification', backref='service', lazy=True)

class ServiceVerification(db.Model):
    __tablename__ = 'service_verification'

    verification_id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('supported_service.service_id'))
    guild_id = db.Column(db.String, db.ForeignKey('affiliated_guild.guild_id'))
    verified_role_id = db.Column(db.String)

class AffiliatedGuild(db.Model):
    __tablename__ = 'affiliated_guild'

    guild_id = db.Column(db.String, primary_key=True)
    guild_hash = db.Column(db.String, nullable=False) # is it worth pre-storing hashes when we store the original value?
    authorized = db.Column(db.Boolean, default=True)
    authorizing_user = db.Column(db.String, db.ForeignKey('user.discord_user_id'))
    authorization_date = db.Column(db.DateTime, default=dt.utcnow)
    last_updated = db.Column(db.DateTime, onupdate=dt.utcnow)

class UserOAuth(db.Model):
    __tablename__ = 'user_oauth'

    discord_user_id = db.Column(db.String, db.ForeignKey('user.discord_user_id'), primary_key=True, nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('supported_service.service_id'), primary_key=True, nullable=False)
    service_user_id = db.Column(db.String)
    service_user_name = db.Column(db.String) # how important is storing this?
    authorized = db.Column(db.Boolean, default=True)
    access_token = db.Column(db.String)
    refresh_token = db.Column(db.String)
    scope = db.Column(db.String)
    first_grant_date = db.Column(db.DateTime, default=dt.utcnow)
    token_expiry_date = db.Column(db.DateTime)
    last_revision_date = db.Column(db.DateTime, onupdate=dt.utcnow)

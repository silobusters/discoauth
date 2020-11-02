"""empty message

Revision ID: a7e371330983
Revises: 
Create Date: 2020-11-01 15:42:56.531913

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7e371330983'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('supported_service',
    sa.Column('service_id', sa.Integer(), nullable=False),
    sa.Column('service_name', sa.String(), nullable=True),
    sa.Column('service_hash', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('service_id')
    )
    op.create_table('user',
    sa.Column('discord_user_id', sa.String(), nullable=False),
    sa.Column('github_user_id', sa.String(), nullable=True),
    sa.Column('github_verified', sa.Boolean(), nullable=True),
    sa.Column('github_event_announce', sa.Boolean(), nullable=True),
    sa.Column('github_entity_reaction', sa.Boolean(), nullable=True),
    sa.Column('github_gist_append', sa.String(), nullable=True),
    sa.Column('stackexchange_user_id', sa.String(), nullable=True),
    sa.Column('stackexchange_assistant_opt_in', sa.Boolean(), nullable=True),
    sa.Column('stackexchange_assistant_topics', sa.String(), nullable=True),
    sa.Column('stackexchange_publisher_opt_in', sa.Boolean(), nullable=True),
    sa.Column('sb_status_id', sa.Integer(), nullable=True),
    sa.Column('creation_date', sa.DateTime(), nullable=True),
    sa.Column('last_updated', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('discord_user_id')
    )
    op.create_table('affiliated_guild',
    sa.Column('guild_id', sa.String(), nullable=False),
    sa.Column('guild_hash', sa.String(), nullable=False),
    sa.Column('authorized', sa.Boolean(), nullable=True),
    sa.Column('verified_role_id', sa.String(), nullable=False),
    sa.Column('authorizing_user', sa.String(), nullable=True),
    sa.Column('authorization_date', sa.DateTime(), nullable=True),
    sa.Column('last_updated', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['authorizing_user'], ['user.discord_user_id'], ),
    sa.PrimaryKeyConstraint('guild_id')
    )
    op.create_table('user_oauth',
    sa.Column('discord_user_id', sa.String(), nullable=False),
    sa.Column('service_id', sa.Integer(), nullable=False),
    sa.Column('authorized', sa.Boolean(), nullable=True),
    sa.Column('token', sa.String(), nullable=True),
    sa.Column('sb_verification_token', sa.String(), nullable=True),
    sa.Column('scope', sa.String(), nullable=True),
    sa.Column('first_grant_date', sa.DateTime(), nullable=True),
    sa.Column('token_expiry_date', sa.DateTime(), nullable=True),
    sa.Column('last_grant_date', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['discord_user_id'], ['user.discord_user_id'], ),
    sa.ForeignKeyConstraint(['service_id'], ['supported_service.service_id'], ),
    sa.PrimaryKeyConstraint('discord_user_id', 'service_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_oauth')
    op.drop_table('affiliated_guild')
    op.drop_table('user')
    op.drop_table('supported_service')
    # ### end Alembic commands ###
"""Add a log for weather downloads

Revision ID: e52cd9d1994b
Revises: 99e2c52dd4c2
Create Date: 2021-09-30 11:21:33.149746

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e52cd9d1994b'
down_revision = '99e2c52dd4c2'
branch_labels = None
depends_on = None

def upgrade():

    op.create_table('weather_fetch_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('station_id', sa.Integer(), nullable=True),
    sa.Column('dtstart', sa.DateTime(), nullable=True),
    sa.Column('dtend', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['station_id'], ['location.id'], name='fk_weather_fetch_log_location_id'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_weather_fetch_log'))
    )

def downgrade():

    op.drop_table('weather_fetch_log')

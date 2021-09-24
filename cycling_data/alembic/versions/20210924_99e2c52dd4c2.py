"""Add a parse_error column to StationWeatherData

Revision ID: 99e2c52dd4c2
Revises: 4c6e10d0ebcc
Create Date: 2021-09-24 17:31:07.830261

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '99e2c52dd4c2'
down_revision = '4c6e10d0ebcc'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('stationweatherdata', schema=None) as batch_op:
        batch_op.add_column(sa.Column('parse_error', sa.Boolean(), nullable=True))

def downgrade():
    with op.batch_alter_table('stationweatherdata', schema=None) as batch_op:
        batch_op.drop_column('parse_error')

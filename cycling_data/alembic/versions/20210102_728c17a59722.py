"""Added log for sent requests

Revision ID: 728c17a59722
Revises: 8908f5e1ad12
Create Date: 2021-01-02 18:07:13.648960

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '728c17a59722'
down_revision = '8908f5e1ad12'
branch_labels = None
depends_on = None

def upgrade():

    op.create_table('sent_request_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=True),
    sa.Column('url', sa.Text(), nullable=True),
    sa.Column('status_code', sa.Integer(), nullable=True),
    sa.Column('rate_limited', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sent_request_log'))
    )

def downgrade():

    op.drop_table('sent_request_log')

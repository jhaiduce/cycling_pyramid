"""Added password field for User

Revision ID: 195cc6626435
Revises: 6fcac516d81a
Create Date: 2019-03-24 19:25:45.635217

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '195cc6626435'
down_revision = '6fcac516d81a'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pw_timestamp', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('pwhash', sa.String(), nullable=True))

def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('pwhash')
        batch_op.drop_column('pw_timestamp')

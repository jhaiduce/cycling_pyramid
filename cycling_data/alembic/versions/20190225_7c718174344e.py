"""Added timezone column to the locations table

Revision ID: 7c718174344e
Revises: ab7d9cf4d1af
Create Date: 2019-02-25 22:21:24.331129

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c718174344e'
down_revision = 'ab7d9cf4d1af'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('ride', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timezone', sa.String(length=255), nullable=True))

def downgrade():
    with op.batch_alter_table('ride', schema=None) as batch_op:
        batch_op.drop_column('timezone')

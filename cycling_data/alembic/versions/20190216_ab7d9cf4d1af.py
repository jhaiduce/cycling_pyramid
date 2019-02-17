"""Added index for Location.name

Revision ID: ab7d9cf4d1af
Revises: e23b4801093c
Create Date: 2019-02-16 18:51:22.671096

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ab7d9cf4d1af'
down_revision = 'e23b4801093c'
branch_labels = None
depends_on = None

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_location_name'), 'location', ['name'], unique=False)
    # ### end Alembic commands ###

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_location_name'), table_name='location')
    # ### end Alembic commands ###

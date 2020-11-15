"""Add unique contraints for name columns

Revision ID: 363c0ba96170
Revises: 195cc6626435
Create Date: 2020-11-14 20:28:09.245672

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '363c0ba96170'
down_revision = '195cc6626435'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.create_unique_constraint(batch_op.f('uq_equipment_name'), ['name'])

    with op.batch_alter_table('location', schema=None) as batch_op:
        batch_op.drop_index('ix_location_name')
        batch_op.create_index(batch_op.f('ix_location_name'), ['name'], unique=True)

    with op.batch_alter_table('locationtype', schema=None) as batch_op:
        batch_op.create_unique_constraint(batch_op.f('uq_locationtype_name'), ['name'])

    with op.batch_alter_table('rider', schema=None) as batch_op:
        batch_op.create_unique_constraint(batch_op.f('uq_rider_name'), ['name'])

    with op.batch_alter_table('ridergroup', schema=None) as batch_op:
        batch_op.create_unique_constraint(batch_op.f('uq_ridergroup_name'), ['name'])

    with op.batch_alter_table('surfacetype', schema=None) as batch_op:
        batch_op.create_unique_constraint(batch_op.f('uq_surfacetype_name'), ['name'])

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_unique_constraint(batch_op.f('uq_user_name'), ['name'])

def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_user_name'), type_='unique')

    with op.batch_alter_table('surfacetype', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_surfacetype_name'), type_='unique')

    with op.batch_alter_table('ridergroup', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_ridergroup_name'), type_='unique')

    with op.batch_alter_table('rider', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_rider_name'), type_='unique')

    with op.batch_alter_table('locationtype', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_locationtype_name'), type_='unique')

    with op.batch_alter_table('location', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_location_name'))
        batch_op.create_index('ix_location_name', ['name'], unique=False)

    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_equipment_name'), type_='unique')

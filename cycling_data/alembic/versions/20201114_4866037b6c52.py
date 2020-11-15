"""Added tables and columns to support storage of prediction model state

Revision ID: 4866037b6c52
Revises: 363c0ba96170
Create Date: 2020-11-14 20:49:53.989070

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4866037b6c52'
down_revision = '363c0ba96170'
branch_labels = None
depends_on = None

def upgrade():
    bind=op.get_bind()

    if bind.engine.name=='sqlite':
        recreate='always'
    else:
        recreate='auto'

    op.create_table('predictionmodel',
    sa.Column('entry_date', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    sa.Column('modified_date', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('weights', sa.Binary(), nullable=True),
    sa.Column('stats', sa.Binary(), nullable=True),
    sa.Column('train_dataset_size', sa.Integer(), nullable=True),
    sa.Column('training_in_progress', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_predictionmodel')),
    mysql_encrypted='yes'
    )
    with op.batch_alter_table('location', schema=None, recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column('entry_date', sa.DateTime(), server_default=sa.func.now(), nullable=True))
        batch_op.add_column(sa.Column('modified_date', sa.DateTime(), server_default=sa.func.now(), nullable=True))

    with op.batch_alter_table('ride', schema=None, recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column('entry_date', sa.DateTime(), server_default=sa.func.now(), nullable=True))
        batch_op.add_column(sa.Column('modified_date', sa.DateTime(), server_default=sa.func.now(), nullable=True))

    with op.batch_alter_table('weatherdata', schema=None, recreate=recreate) as batch_op:
        batch_op.add_column(sa.Column('entry_date', sa.DateTime(), server_default=sa.func.now(), nullable=True))
        batch_op.add_column(sa.Column('modified_date', sa.DateTime(), server_default=sa.func.now(), nullable=True))

def downgrade():
    with op.batch_alter_table('weatherdata', schema=None) as batch_op:
        batch_op.drop_column('modified_date')
        batch_op.drop_column('entry_date')

    with op.batch_alter_table('ride', schema=None) as batch_op:
        batch_op.drop_column('modified_date')
        batch_op.drop_column('entry_date')

    with op.batch_alter_table('location', schema=None) as batch_op:
        batch_op.drop_column('modified_date')
        batch_op.drop_column('entry_date')

    op.drop_table('predictionmodel')

"""New/changed fields for better serialization of model parameters

Revision ID: 8908f5e1ad12
Revises: 4866037b6c52
Create Date: 2020-11-25 19:54:09.614232

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8908f5e1ad12'
down_revision = '4866037b6c52'
branch_labels = None
depends_on = None

def upgrade():

    with op.batch_alter_table('predictionmodel', schema=None) as batch_op:
        batch_op.add_column(sa.Column('input_columns', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('input_size', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('predict_columns', sa.Text(), nullable=True))
        batch_op.alter_column('stats',
               existing_type=sa.BLOB(),
               type_=sa.Text(),
               existing_nullable=True)

def downgrade():

    with op.batch_alter_table('predictionmodel', schema=None) as batch_op:
        batch_op.alter_column('stats',
               existing_type=sa.Text(),
               type_=sa.BLOB(),
               existing_nullable=True)
        batch_op.drop_column('predict_columns')
        batch_op.drop_column('input_size')
        batch_op.drop_column('input_columns')

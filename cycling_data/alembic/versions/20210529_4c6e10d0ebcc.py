"""Add avspeed, maxspeed, and total_time columns to PredictionModelResult

Revision ID: 4c6e10d0ebcc
Revises: d372d3e1a794
Create Date: 2021-05-29 20:04:26.375295

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c6e10d0ebcc'
down_revision = 'd372d3e1a794'
branch_labels = None
depends_on = None

def upgrade():

    with op.batch_alter_table('predictionmodel_result', schema=None) as batch_op:
        batch_op.add_column(sa.Column('avspeed', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('maxspeed', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('total_time', sa.Float(), nullable=True))

    with op.batch_alter_table('predictionmodel', schema=None) as batch_op:
        batch_op.add_column(sa.Column('output_size', sa.Integer(), nullable=True))

    predictionmodel_result=sa.table(
        'predictionmodel_result',
        sa.column('result',sa.Float()),
        sa.column('avspeed',sa.Float())
    )

    conn=op.get_bind()

    result = conn.execute(
        predictionmodel_result.update(
        ).values(
            avspeed=sa.text('result')
        )
    )

def downgrade():

    with op.batch_alter_table('predictionmodel_result', schema=None) as batch_op:
        batch_op.drop_column('total_time')
        batch_op.drop_column('maxspeed')
        batch_op.drop_column('avspeed')

    with op.batch_alter_table('predictionmodel', schema=None) as batch_op:
        batch_op.drop_column('output_size')


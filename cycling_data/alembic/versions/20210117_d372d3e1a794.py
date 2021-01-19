"""Added table to store prediction model results

Revision ID: d372d3e1a794
Revises: 728c17a59722
Create Date: 2021-01-17 15:57:18.287030

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd372d3e1a794'
down_revision = '728c17a59722'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('predictionmodel_result',
    sa.Column('entry_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('modified_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('model_id', sa.Integer(), nullable=True),
    sa.Column('ride_id', sa.Integer(), nullable=True),
    sa.Column('result', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['model_id'], ['predictionmodel.id'], name=op.f('fk_predictionmodel_result_model_id_predictionmodel')),
    sa.ForeignKeyConstraint(['ride_id'], ['ride.id'], name=op.f('fk_predictionmodel_result_ride_id_ride')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_predictionmodel_result')),
    mysql_encrypted='yes'
    )


def downgrade():
    op.drop_table('predictionmodel_result')

"""Add module details column for holding tfsec output

Revision ID: d499042fad3b
Revises: 47e45e505e22
Create Date: 2022-07-04 22:14:53.819081

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'd499042fad3b'
down_revision = '47e45e505e22'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('module_details', sa.Column('tfsec', sa.LargeBinary(length=16777215).with_variant(mysql.MEDIUMBLOB(), 'mysql'), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('module_details', 'tfsec')
    # ### end Alembic commands ###
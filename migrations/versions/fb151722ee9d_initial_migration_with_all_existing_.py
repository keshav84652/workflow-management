"""Initial migration with all existing tables

Revision ID: fb151722ee9d
Revises: 
Create Date: 2025-06-08 08:43:27.681135

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fb151722ee9d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('attachment', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.INTEGER(),
               nullable=False,
               autoincrement=True)

    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.alter_column('hourly_rate',
               existing_type=sa.REAL(),
               type_=sa.Float(),
               existing_nullable=True)
        batch_op.alter_column('recurrence_rule',
               existing_type=sa.TEXT(),
               type_=sa.String(length=100),
               existing_nullable=True)
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(None, 'task', ['parent_task_id'], ['id'], ondelete='CASCADE')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(None, 'task', ['parent_task_id'], ['id'])
        batch_op.alter_column('recurrence_rule',
               existing_type=sa.String(length=100),
               type_=sa.TEXT(),
               existing_nullable=True)
        batch_op.alter_column('hourly_rate',
               existing_type=sa.Float(),
               type_=sa.REAL(),
               existing_nullable=True)

    with op.batch_alter_table('attachment', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.INTEGER(),
               nullable=True,
               autoincrement=True)

    # ### end Alembic commands ###

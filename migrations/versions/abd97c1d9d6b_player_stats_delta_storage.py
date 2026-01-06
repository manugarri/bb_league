"""player_stats_delta_storage

Revision ID: abd97c1d9d6b
Revises: 
Create Date: 2026-01-05 22:34:04.152864

This migration converts player stat storage from absolute values to delta/modifier
values (difference from base position stats). This reduces data redundancy since
most players have the same stats as their base position.

Old schema: movement, strength, agility, passing, armor (absolute values)
New schema: movement_mod, strength_mod, agility_mod, passing_mod, armor_mod (deltas)

The effective stat is now computed as: base_position_stat + modifier
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abd97c1d9d6b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Get connection for data migration
    conn = op.get_bind()
    
    # Check if old columns exist (existing database) or not (fresh database)
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('players')]
    has_old_columns = 'movement' in existing_columns and 'movement_mod' not in existing_columns
    
    if has_old_columns:
        # EXISTING DATABASE: Migrate data from absolute to delta storage
        
        # Step 1: Add new modifier columns
        with op.batch_alter_table('players', schema=None) as batch_op:
            batch_op.add_column(sa.Column('movement_mod', sa.Integer(), nullable=True, server_default='0'))
            batch_op.add_column(sa.Column('strength_mod', sa.Integer(), nullable=True, server_default='0'))
            batch_op.add_column(sa.Column('agility_mod', sa.Integer(), nullable=True, server_default='0'))
            batch_op.add_column(sa.Column('passing_mod', sa.Integer(), nullable=True, server_default='0'))
            batch_op.add_column(sa.Column('armor_mod', sa.Integer(), nullable=True, server_default='0'))
        
        # Step 2: Calculate and set delta values from old absolute values
        # delta = player_stat - position_base_stat
        conn.execute(sa.text("""
            UPDATE players 
            SET 
                movement_mod = COALESCE(players.movement, 0) - COALESCE((SELECT positions.movement FROM positions WHERE positions.id = players.position_id), 0),
                strength_mod = COALESCE(players.strength, 0) - COALESCE((SELECT positions.strength FROM positions WHERE positions.id = players.position_id), 0),
                agility_mod = COALESCE(players.agility, 0) - COALESCE((SELECT positions.agility FROM positions WHERE positions.id = players.position_id), 0),
                passing_mod = COALESCE(players.passing, 0) - COALESCE((SELECT positions.passing FROM positions WHERE positions.id = players.position_id), 0),
                armor_mod = COALESCE(players.armor, 0) - COALESCE((SELECT positions.armor FROM positions WHERE positions.id = players.position_id), 0)
        """))
        
        # Step 3: Drop old columns
        with op.batch_alter_table('players', schema=None) as batch_op:
            batch_op.drop_column('passing')
            batch_op.drop_column('strength')
            batch_op.drop_column('movement')
            batch_op.drop_column('agility')
            batch_op.drop_column('armor')
    
    elif 'movement_mod' not in existing_columns:
        # FRESH DATABASE: Just add the new columns (old columns don't exist)
        with op.batch_alter_table('players', schema=None) as batch_op:
            batch_op.add_column(sa.Column('movement_mod', sa.Integer(), nullable=True, server_default='0'))
            batch_op.add_column(sa.Column('strength_mod', sa.Integer(), nullable=True, server_default='0'))
            batch_op.add_column(sa.Column('agility_mod', sa.Integer(), nullable=True, server_default='0'))
            batch_op.add_column(sa.Column('passing_mod', sa.Integer(), nullable=True, server_default='0'))
            batch_op.add_column(sa.Column('armor_mod', sa.Integer(), nullable=True, server_default='0'))
    
    # else: Both old and new columns exist - migration already partially applied, skip


def downgrade():
    # Get connection for data migration
    conn = op.get_bind()
    
    # Check current state
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('players')]
    has_mod_columns = 'movement_mod' in existing_columns
    has_old_columns = 'movement' in existing_columns
    
    if has_mod_columns and not has_old_columns:
        # Restore old columns and convert deltas back to absolute values
        
        # Step 1: Add old columns back
        with op.batch_alter_table('players', schema=None) as batch_op:
            batch_op.add_column(sa.Column('armor', sa.INTEGER(), nullable=True))
            batch_op.add_column(sa.Column('agility', sa.INTEGER(), nullable=True))
            batch_op.add_column(sa.Column('movement', sa.INTEGER(), nullable=True))
            batch_op.add_column(sa.Column('strength', sa.INTEGER(), nullable=True))
            batch_op.add_column(sa.Column('passing', sa.INTEGER(), nullable=True))
        
        # Step 2: Convert delta values back to absolute values
        # absolute = position_base_stat + delta
        conn.execute(sa.text("""
            UPDATE players 
            SET 
                movement = COALESCE((SELECT positions.movement FROM positions WHERE positions.id = players.position_id), 0) + COALESCE(players.movement_mod, 0),
                strength = COALESCE((SELECT positions.strength FROM positions WHERE positions.id = players.position_id), 0) + COALESCE(players.strength_mod, 0),
                agility = COALESCE((SELECT positions.agility FROM positions WHERE positions.id = players.position_id), 0) + COALESCE(players.agility_mod, 0),
                passing = COALESCE((SELECT positions.passing FROM positions WHERE positions.id = players.position_id), 0) + COALESCE(players.passing_mod, 0),
                armor = COALESCE((SELECT positions.armor FROM positions WHERE positions.id = players.position_id), 0) + COALESCE(players.armor_mod, 0)
        """))
        
        # Step 3: Drop new columns
        with op.batch_alter_table('players', schema=None) as batch_op:
            batch_op.drop_column('armor_mod')
            batch_op.drop_column('passing_mod')
            batch_op.drop_column('agility_mod')
            batch_op.drop_column('strength_mod')
            batch_op.drop_column('movement_mod')

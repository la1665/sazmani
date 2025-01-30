from sqlalchemy import Table, Column, Integer, ForeignKey

from database.engine import Base


user_gate_access = Table(
    'user_gate_access',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('gate_id', Integer, ForeignKey('gates.id', ondelete="CASCADE"), primary_key=True),
)

guest_gate_access = Table(
    'guest_gate_access',
    Base.metadata,
    Column('guest_id', Integer, ForeignKey('guests.id', ondelete="CASCADE"), primary_key=True),
    Column('gate_id', Integer, ForeignKey('gates.id', ondelete="CASCADE"), primary_key=True),
)

viewer_gate_access = Table(
    'viewer_gate_access',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('gate_id', Integer, ForeignKey('gates.id', ondelete="CASCADE"), primary_key=True),
)

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from metalbender.data_access._base import Base


class GceInstance(Base):
    __tablename__ = 'gce_instance'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    name = Column('name', String, nullable=False)
    project_id = Column('project_id', String, nullable=False)
    zone = Column('zone', String, nullable=False)

    __table_args__ = (
        Index('idx_resource_type_id', 'project_id'),
        Index('idx_resource_type_id', 'zone'),
    )


class Heartbeat(Base):
    __tablename__ = 'heartbeat'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    instance_id = Column('instance_id', Integer, ForeignKey(f'{GceInstance.__tablename__}.id'), nullable=False)
    added = Column('added', DateTime, nullable=False)
    deadline = Column('deadline', DateTime, nullable=False)

    gce_instance = relationship("GceInstance")

    # Index on resource name and time reqiested.
    __table_args__ = (
        Index('idx_heartbeat_deadline', 'deadline'),
        Index('idx_heartbeat_instance_id', 'instance_id'),
    )

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String

from metalbender.data_access._base import Base

RESOURCE_TYPES: list[str] = [
    'GCE_INSTANCE',
]


class ResourceType(Base):
    __tablename__ = 'resource_type'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)


class Heartbeat(Base):
    __tablename__ = 'heartbeat'

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_name = Column(String, nullable=False)
    resource_type_id = Column(Integer, ForeignKey(f'{ResourceType.__tablename__}.id'), nullable=False)
    time_added = Column(DateTime, nullable=False)
    time_requested = Column(DateTime, nullable=False)

    # Index on resource name and time reqiested.
    __table_args__ = (
        Index('idx_heartbeat_resource_name_time_requested', 'resource_name', 'time_requested'),
    )

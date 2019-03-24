from sqlalchemy import (
    Column,
    Index,
    Integer,
    String,
    Float,
    ForeignKey,
    Sequence,
    DateTime,
    Boolean,
    Interval
)
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import relationship

from .meta import Base

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, Sequence('locationtype_seq'), primary_key=True)
    name = Column(String)

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
from datetime import datetime

from .meta import Base

import bcrypt

class User(Base):
    __tablename__ = 'user'
    __table_args__ = {'mysql_encrypted':'yes'}
    
    id = Column(Integer, Sequence('locationtype_seq'), primary_key=True)
    name = Column(String(255),unique=True)
    pwhash = Column(String(255))
    pw_timestamp = Column(DateTime)

    def check_password(self,pw):
        return bcrypt.checkpw(pw.encode('utf8'), self.pwhash.encode('utf8'))

    def set_password(self,pw):

        self.pwhash = bcrypt.hashpw(
            pw.encode('utf8'), bcrypt.gensalt()
        ).decode('utf-8')

        self.pw_timestamp=datetime.now()

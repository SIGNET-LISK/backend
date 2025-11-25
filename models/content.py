from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from sqlalchemy.sql import func
from indexer.db import Base

class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    phash = Column("phash", String, unique=True, index=True, nullable=False)
    publisher = Column(String, index=True, nullable=False)
    title = Column(String)
    description = Column(String)
    timestamp = Column(BigInteger)
    txhash = Column("txhash", String)
    blocknumber = Column("blocknumber", Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

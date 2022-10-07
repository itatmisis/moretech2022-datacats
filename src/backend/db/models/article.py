"""Article model for SQLAlchemy"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, Boolean, Text, Date
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Article(Base):
    """Article model for PostgreSQL"""
    __tablename__ = "articles"
    id = Column(Text, primary_key=True)
    source = Column(Text)  # rbc, ...
    topic = Column(Text)
    title = Column(Text)
    preamble = Column(Text)
    tldr = Column(Text)
    body = Column(Text)

    def __repr__(self):
        return f"<Article(id={self.id}, source={self.source}, topic={self.topic}, title={self.title}, preamble={self.preamble}, tldr={self.tldr}, body={self.body})>"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

#!/usr/bin/env python3

from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy_utils import database_exists, create_database
from typing import List, Union
from sqlalchemy import text
from time import mktime

# Models
from os import getenv
from dotenv import load_dotenv
load_dotenv()
if getenv("DOCKER_MODE") != "true":
    from models.article import Base, Article
else:
    from db.models.article import Base, Article
# Error handling
from time import sleep
from sqlalchemy.exc import OperationalError as sqlalchemyOpError
from psycopg2 import OperationalError as psycopg2OpError

class DB:
    def __init__(self, db_creds) -> None:
        connected = False
        while not connected:
            try:
                self.connect(db_creds["user"],
                             db_creds["pass"],
                             db_creds["host"],
                             db_creds["port"])
            except (sqlalchemyOpError, psycopg2OpError):
                sleep(2)
            else:
                connected = True
        # Create table if it doesn't exist
        if not database_exists(self.engine.url):
            create_database(self.engine.url)
            # Update tables to create relations in db
            self.recreate_tables()

    # region Connection setup
    def connect(self, pg_user, pg_pass, pg_host, pg_port) -> None:
        self.engine = create_engine(f"postgresql+psycopg2://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/articles")
        # Create session
        Base.metadata.bind = self.engine
        db_session = sessionmaker(bind=self.engine)
        self.session = db_session()

    def update_tables(self) -> None:
        Base.metadata.create_all(self.engine)

    def recreate_tables(self) -> None:
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def close(self) -> None:
        """Closes the database connection"""
        self.session.close_all()
    # endregion
    # region Article management
    def article_exists(self, article_id: str) -> bool:
        return self.session.query(Article.id).filter_by(id=article_id).first() is not None

    def add_article(self, article_id: str, article_data: dict) -> None:
        if not self.article_exists(article_id):
            article = Article(id=article_id,
                              source=article_data["source"],
                              topic=article_data["topic"],
                              title=article_data["title"],
                              preamble=article_data["preamble"],
                              tldr=article_data["tldr"],
                              timestamp=article_data["timestamp"],
                              body=article_data["body"])
            self.session.add(article)
            self.session.commit()

    def get_stats(self) -> dict:
        article_count = self.session.execute("SELECT COUNT(*) FROM articles").first()[0]  # TODO: Fix [0] with a better solution
        return {"article_count": article_count}

    def get_ids(self) -> list:
        #return [article.id for article in self.session.query().all()]
        return self.session.scalars(self.session.query(Article.id)).all()

    def get_ids_by_source(self, source: str) -> list:
        return self.session.scalars(self.session.query(Article.id).filter_by(source=source)).all()

    def get_title(self, article_id: str) -> str:
        return self.session.query(Article).get(article_id).title

    def get_article(self, article_id: str) -> dict:
        article = self.session.query(Article).get(article_id).as_dict()
        article["timestamp"] = int(mktime(article["timestamp"].timetuple()))
        return article

    def get_all_articles(self) -> dict:
        articles_raw = self.session.execute(text("SELECT id, source, topic, title, preamble, tldr, timestamp, body FROM articles")).all()
        articles = {}
        for article in articles_raw:
            articles[article[0]] = {"source": article[1],
                                    "topic": article[2],
                                    "title": article[3],
                                    "preamble": article[4],
                                    "tldr": article[5],
                                    "timestamp": int(mktime(article[6].timetuple())),
                                    "body": article[7]}  # timestamp is returned as UTC UNIX Time
        return articles

    def get_all_articles_meta(self) -> dict:
        articles_raw = self.session.execute(text("SELECT id, source, topic, title, preamble, tldr, timestamp FROM articles")).all()
        articles = {}
        for article in articles_raw:
            articles[article[0]] = {"source": article[1],
                                    "topic": article[2],
                                    "title": article[3],
                                    "preamble": article[4],
                                    "tldr": article[5],
                                    "timestamp": int(mktime(article[6].timetuple()))}
        return articles

    def get_all_articles_body(self) -> dict:
        articles_raw = self.session.execute(text("SELECT id, body FROM articles")).all()
        articles = {}
        for article in articles_raw:
            articles[article[0]] = {"body": article[1]}
        return articles

    def get_article_body(self, article_id: str) -> str:
        return self.session.query(Article).get(article_id).body

    def get_article_meta(self, article_id: str) -> dict:
        article_raw = self.session.execute(text(f"SELECT source, topic, title, preamble, tldr, timestamp FROM articles WHERE id = '{article_id}'")).first()
        return {"source": article_raw[0],
                "topic": article_raw[1],
                "title": article_raw[2],
                "preamble": article_raw[3],
                "tldr": article_raw[4],
                "timestamp": int(mktime(article[5].timetuple()))}

if __name__ == "__main__":
    from os import getenv
    from dotenv import load_dotenv
    load_dotenv()
    db_creds = {"user": getenv("DATACATS_PSQL_USER"),
                "pass": getenv("DATACATS_PSQL_PASS"),
                "host": getenv("DATACATS_PSQL_HOST"),
                "port": getenv("DATACATS_PSQL_PORT")}
    db = DB(db_creds)
    #print(db.get_ids_by_source("rbc-technology_and_media"))
    #!print(db.get_meta('631acf519a79476d2fe21e12'))
    #print(db.get_all_articles())
    print(db.get_article("ria-yandeks-1816257822"))

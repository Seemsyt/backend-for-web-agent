from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,Session
from sqlalchemy.engine import create_engine
from dotenv import load_dotenv
from os import getenv
from typing import Generator
load_dotenv()
Base = declarative_base()

engine = create_engine(getenv("URL"))

Session_loacal = sessionmaker(autocommit = False,bind=engine,autoflush=False)

def get_db()->Generator[Session,None,None]:
    db = Session_loacal()
    try:
        yield db
    finally:
        db.close()
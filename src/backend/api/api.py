from os import getenv             # Interact with environment variables
from fastapi import FastAPI       # Main API
import logging                    # Logging important events
from dotenv import load_dotenv    # Load environment variables from .env
from db.alchemy import DB         # Connect to db
# Security
#from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# region Logging
# Create a logger instance
log = logging.getLogger('datacats-backend-api')
# Create log formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Сreate console logging handler and set its level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
log.addHandler(ch)

# region Docker check
# Check if we are under Docker
DOCKER_MODE = False
if getenv("DOCKER_MODE") == 'true':
    DOCKER_MODE = True
    log.warning("Docker mode enabled")
else:
    log.warning("Docker mode disabled")

# Load environment variables from .env file
if not DOCKER_MODE:
    load_dotenv()
# endregion

# Create file logging handler and set its level
if DOCKER_MODE:
    logfile_path = r"/data/datacats-moretech-backend-api.log"
else:
    logfile_path = r"datacats-moretech-backend-api.log"
fh = logging.FileHandler(logfile_path)
fh.setFormatter(formatter)
log.addHandler(fh)

# Set logging level
logging_level_lower = getenv('DATACATS_LOGGING_LEVEL').lower()
if logging_level_lower == 'debug':
    log.setLevel(logging.DEBUG)
    log.critical("Log level set to debug")
elif logging_level_lower == 'info':
    log.setLevel(logging.INFO)
    log.critical("Log level set to info")
elif logging_level_lower == 'warning':
    log.setLevel(logging.WARNING)
    log.critical("Log level set to warning")
elif logging_level_lower == 'error':
    log.setLevel(logging.ERROR)
    log.critical("Log level set to error")
elif logging_level_lower == 'critical':
    log.setLevel(logging.CRITICAL)
    log.critical("Log level set to critical")
# endregion

# region DB
# DB authentication credentials dict
db_creds = {"user": getenv("DATACATS_PSQL_USER"),
            "pass": getenv("DATACATS_PSQL_PASS"),
            "host": getenv("DATACATS_PSQL_HOST"),
            "port": getenv("DATACATS_PSQL_PORT")}

# Open connection with DB
db = DB(db_creds)

# Create FastAPI app
app = FastAPI()
log.debug("FastAPI is up")

# FastAPI authentication
#! OH NO! It's insecure!

@app.get("/")
async def root():
    return {"message": "It's alive!"}
    log.debug("FastAPI: A user requested /")

@app.get("/stats")
async def get_stats():
    log.debug("FastAPI: A user requested /stats")
    return db.get_stats()

@app.get("/sources")
async def get_sources():
    log.debug("FastAPI: A user requested /sources")
    return {}

@app.get("/articles")
async def get_article_list():
    log.debug("FastAPI: A user requested /articles")
    return db.get_ids()

@app.get("/articles/all")
async def get_all_articles():
    log.debug("FastAPI: A user requested /articles/all")
    return db.get_all_articles()

@app.get("/articles/all/meta")
async def get_all_articles_meta():
    log.debug("FastAPI: A user requested /articles/all/meta")
    return db.get_all_articles_meta()

@app.get("/articles/all/body")
async def get_all_articles_body():
    log.debug("FastAPI: A user requested /articles/all/body")
    return db.get_all_articles_body()

@app.get("/article/{article_id}")
async def get_article(article_id):
    log.debug(f"FastAPI: A user requested /article/{article_id}")
    return db.get_article(article_id)

@app.get("/article/{article_id}/meta")
async def get_article_meta(article_id):
    log.debug(f"FastAPI: A user requested /article/{article_id}/meta")
    return db.get_article_meta(article_id)

@app.get("/article/{article_id}/body")
async def get_article_body(article_id):
    log.debug(f"FastAPI: A user requested /article/{article_id}/body")
    return {"body": db.get_article_body(article_id)}

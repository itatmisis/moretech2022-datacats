from os import getenv             # Interact with environment variables
from fastapi import FastAPI       # Main API
import logging                    # Logging important events
from dotenv import load_dotenv    # Load environment variables from .env
from db.alchemy import DB         # Connect to db
from newsparser import RBCParser  # www.rbc.ru parser
# Security
#from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# region Logging
# Create a logger instance
log = logging.getLogger('datacats-backend-parsers')
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
    logfile_path = r"/data/datacats-moretech-backend-parser.log"
else:
    logfile_path = r"datacats-moretech-backend-parser.log"
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
log.debug("API DB connection is up")
# endregion

# Create parser instances
rbc = RBCParser(log,
                4,
                getenv("DATACATS_SELENIUM_DOMAIN"),
                getenv("DATACATS_SELENIUM_PORT"),
                db_creds)
log.debug("RBCParser is up")

# Create FastAPI app
app = FastAPI()
log.debug("FastAPI is up")

@app.get("/")
async def root():
    return {"message": "It's alive!"}
    log.debug("FastAPI: A user requested /")

# TODO: Replace with a scheduler
@app.post("/articles/fetch/{topic}")  #! Parser is in another docker container!
async def fetch_articles(topic):
    if rbc.is_fetching():
        log.debug(f"FastAPI: A user requested /articles/fetch/{topic}; another request is in progress, aborting")
        return {"fetched": False, "reason": "fetch_in_progress", "target": topic}
    log.debug(f"FastAPI: A user requested /articles/fetch/{topic}")
    rbc.fetch(topic)
    return {"fetched": True, "reason": None, "target": topic}
#!/usr/bin/env python3

from os import getenv                # Interact with environment variables
from fastapi import FastAPI          # Main API
from fastapi import BackgroundTasks  # Send response before task termination (0)
import logging                       # Logging important events
from dotenv import load_dotenv       # Load environment variables from .env
from db.alchemy import DB            # Connect to db
from nn import Model

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
    logfile_path = r"/data/datacats-moretech-neuralnet.log"
else:
    logfile_path = r"datacats-moretech-neuralnet.log"
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

# Create NN instance
model = Model(getenv("DATACATS_NN_DATASET_PATH"),
              getenv("DATACATS_NN_DESC_DIRECTOR_PATH"),
              getenv("DATACATS_NN_DESC_ACCOUNTANT_PATH"))
log.info("Model is up")

# Create FastAPI app
app = FastAPI()
log.debug("FastAPI is up")

@app.get("/")
async def root():
    return {"message": "It's alive!"}
    log.debug("FastAPI: A user requested /")

@app.get("/predict/director")
async def predict_director():
    return model.test_director()

@app.get("/predict/accountant")
async def predict_accountant():
    return model.test_accountant()

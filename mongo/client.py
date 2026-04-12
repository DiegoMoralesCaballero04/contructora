import logging
from functools import lru_cache
from pymongo import MongoClient
from django.conf import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    host = getattr(settings, 'MONGO_HOST', 'localhost')
    port = getattr(settings, 'MONGO_PORT', 27017)
    user = getattr(settings, 'MONGO_USER', '')
    password = getattr(settings, 'MONGO_PASSWORD', '')

    if user and password:
        uri = f'mongodb://{user}:{password}@{host}:{port}/'
    else:
        uri = f'mongodb://{host}:{port}/'

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    logger.info('MongoDB client created: %s:%s', host, port)
    return client


def get_db():
    client = get_mongo_client()
    db_name = getattr(settings, 'MONGO_DB', 'construtech_raw')
    return client[db_name]

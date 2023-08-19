import logging

from components.environment import LOG_LEVEL

logger = logging.getLogger("observatory") #type: ignore
logger.setLevel(LOG_LEVEL)
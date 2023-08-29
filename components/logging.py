import logging

from components.environment import LOG_LEVEL

logger = logging.getLogger("ad-processor")  # type: ignore
logger.setLevel(LOG_LEVEL)

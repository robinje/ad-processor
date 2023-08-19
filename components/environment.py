import os

REGION = os.environ.get("AWS_REGION", "us-east-1")

LOG_LEVEL = int(os.environ.get("LOGGING", 20))

DATABASE_NAME = os.environ.get("DATABASE_NAME", "ad-processor")

TS_PAGE_SIZE = 100

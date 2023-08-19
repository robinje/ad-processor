import os

REGION = os.environ.get("AWS_REGION", "us-east-1")

LOG_LEVEL = int(os.environ.get("LOGGING", 20))

DATABASE_NAME = os.environ.get("DATABASE_NAME", "ad-processor")

TABLE_NAME = os.environ.get("DATABASE_NAME", "login")

TS_PAGE_SIZE = 100

CLIENT_ID = "your_client_id"

TENANT_ID = "your_tenant_id"

CLIENT_SECRET = "your_client_secret"

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "your access toknen")

RESOURCE = "https://graph.microsoft.com"

API_VERSION = "v1.0"

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/token"

SNS_TOPIC = os.environ.get("SNS_TOPIC", "arn:aws:sns:us-east-1:123456789012:ad-processor")

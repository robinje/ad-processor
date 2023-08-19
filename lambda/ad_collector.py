from datetime import datetime, timedelta

import pandas as pd
import requests  # type: ignore

from components.azure import azure_token
from components.environment import DATABASE_NAME, TABLE_NAME, RESOURCE, API_VERSION
from components.timestream import timestream_record, timeseries_add_batch


def lambda_handler(event, context):
    # Time filter for last 30 minutes
    time_filter = (datetime.utcnow() - timedelta(minutes=30)).isoformat() + "Z"
    SIGN_IN_LOG_URL: str = f"https://{RESOURCE}/{API_VERSION}/auditLogs/signIns?$filter=createdDateTime ge {time_filter}"

    # Get Token
    token = azure_token()

    # Fetch Azure AD Sign-in Logs
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.get(SIGN_IN_LOG_URL, headers=headers)

    if response.status_code == 200:
        logs = response.json()
        logs_df = pd.json_normalize(logs["value"])

        # Write to Timestream
        records = []

        for _, row in logs_df.iterrows():
            records.append(timestream_record(
                {
                    "username": row["userPrincipalName"],
                    "ip_address": row["ipAddress"],
                    "location": row["location"],
                },
                "success",
                row["status"] == "Success",
                "BOOLEAN",
                int((round(datetime.strptime(row['Date'], "%Y-%m-%dT%H:%M:%SZ").timestamp() * 1000)))
            ))

        timeseries_add_batch(TABLE_NAME, records)

        # Publish the success message
        message = f"Sign-in logs have been written to Timestream: {DATABASE_NAME}/{TABLE_NAME}"
        return {"statusCode": 200, "body": message}
    else:
        error_message = f"Error fetching logs: {response.status_code}, {response.text}"
        return {"statusCode": 500, "body": error_message}

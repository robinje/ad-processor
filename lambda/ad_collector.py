from datetime import datetime, timedelta

import boto3
import pandas as pd
import requests  # type: ignore

from components.environment import DATABASE_NAME, TABLE_NAME, CLIENT_ID, CLIENT_SECRET, RESOURCE, API_VERSION, TOKEN_URL


# Endpoints (Updated to sign-in logs)


def lambda_handler(event, context):
    # Time filter for last 30 minutes
    time_filter = (datetime.utcnow() - timedelta(minutes=30)).isoformat() + "Z"
    SIGN_IN_LOG_URL: str = f"{RESOURCE}/{API_VERSION}/auditLogs/signIns?$filter=createdDateTime ge {time_filter}"

    # Get Token
    token_data = {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "resource": RESOURCE,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }

    token_r = requests.post(TOKEN_URL, data=token_data)
    token = token_r.json().get("access_token")

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
        for index, row in logs_df.iterrows():
            # Example: Mapping specific fields as measures and dimensions
            record = {
                "Time": str(int(pd.to_datetime(row["createdDateTime"]).timestamp() * 1000)),
                "Dimensions": [
                    {"Name": "userPrincipalName", "Value": row["userPrincipalName"]},
                    {"Name": "appId", "Value": row["appId"]},
                    # Add other dimensions as needed
                ],
                "MeasureName": "status_errorCode",  # Example measure
                "MeasureValue": str(row["status.errorCode"]),  # Example measure value
                "MeasureValueType": "BIGINT",  # Type should match the measure value
            }
            records.append(record)

        timestream_client = boto3.client("timestream-write")
        timestream_client.write_records(DatabaseName=DATABASE_NAME, TableName=TABLE_NAME, Records=records)

        # Publish the success message
        message = f"Sign-in logs have been written to Timestream: {DATABASE_NAME}/{TABLE_NAME}"
        return {"statusCode": 200, "body": message}
    else:
        error_message = f"Error fetching logs: {response.status_code}, {response.text}"
        return {"statusCode": 500, "body": error_message}

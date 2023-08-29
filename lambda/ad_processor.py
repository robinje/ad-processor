import json

from components.environment import DATABASE_NAME, TABLE_NAME, SNS_TOPIC
from components.logging import logger
from components.sns import transmit_report
from components.timestream import timeseries_long_query


def collect_data() -> list:
    timestream_query = f"""
        WITH user_most_common_location AS (
            SELECT username, location, RANK() OVER (PARTITION BY username ORDER BY COUNT(*) DESC) as rank
            FROM "{DATABASE_NAME}"."{TABLE_NAME}"
            WHERE time BETWEEN ago(1h) AND now()
            GROUP BY username, location
        ),
        non_common_locations AS (
            SELECT username, location
            FROM user_most_common_location
            WHERE rank > 1
        )

        -- Query for non-common locations
        SELECT t.username, t.ip_address, t.location, t.measure_name, t.time
        FROM "{DATABASE_NAME}"."{TABLE_NAME}" AS t
        JOIN non_common_locations AS n
        ON t.username = n.username AND t.location = n.location
        WHERE t.time BETWEEN ago(1h) AND now()

        UNION

        -- Query for records where success is not true
        SELECT username, ip_address, location, measure_name, time
        FROM "{DATABASE_NAME}"."{TABLE_NAME}"
        WHERE measure_value::boolean
        AND time BETWEEN ago(1h) AND now()
    """

    try:
        timestream_data = timeseries_long_query(timestream_query)
    except Exception as err:
        logger.exception(f"Error while running query: {timestream_query} Error: {err}", stack_info=True)
        return []

    return timestream_data


def lambda_handler(event, context):
    try:
        data = collect_data()

        if data:
            transmit_report(SNS_TOPIC, data)

        return {"statusCode": 200, "body": json.dumps("Success")}
    except Exception as err:
        logger.exception(f"Error in Lambda function: {err}", stack_info=True)
        return {"statusCode": 500, "body": json.dumps(f"Server error: {err}")}

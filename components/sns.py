import json

import boto3

from components.logging import logger

sns_client = boto3.client("sns")


def transmit_report(topic: str, data) -> None:
    sns_client.publish(TopicArn=topic, Message=json.dumps(data), Subject="Non-common Locations and Unsuccessful Attempts")
    logger.info(f"Data sent to SNS topic: {topic}")

import random
import string
from datetime import datetime

import boto3
from botocore.exceptions import ParamValidationError

from components.environment import DATABASE_NAME, REGION, TS_PAGE_SIZE
from components.logging import logger

class TimeStreamWriter:
    def __init__(self):
        self.status = None

        try:
            self.writer = boto3.client("timestream-write", region_name=REGION)
        except Exception as err:
            logger.exception(f"Timestream Handler: Could not connect to Timestream: Unknown Error: {err}", stack_info=True)

            self.status = {"statusCode": 503, "body": {"message": "[Service Unavailable] Timestream database is unreachable"}}

    @xray_recorder.capture("Timestream")  # type: ignore
    def write_records(self, write_args: dict, table):
        try:
            self.writer.write_records(
                DatabaseName=DATABASE_NAME,
                TableName=table.value.lower(),
                **write_args,
            )
        except self.writer.exceptions.RejectedRecordsException as err:
            logger.warning(f"Timestream Handler: RejectedRecords: {err}")
            for rr in err.response["RejectedRecords"]:
                logger.info(f"Timestream Handler: Rejected Index {rr.get('RecordIndex')}: {rr.get('Reason')}")
        except ParamValidationError as err:
            logger.error(f"Timestream Handler: Paramater Validation Error: {write_args}: {err}")
        except Exception as err:
            logger.exception(f"Timestream Handler: Write Records: Unknown Error: {err}", stack_info=True)


    def drop(self, table):
        """Drop the selected table"""

        result = None

        try:
            result = self.writer.delete_table(DatabaseName=DATABASE_NAME, TableName=table)
        except self.writer.exceptions.ResourceNotFoundException:
            logger.error(f"Timestream Handler: Drop: Table {table} does not exist.")
        except Exception as err:
            logger.exception(f"Timestream Handler: Drop: Table {table} failed to be deleted: Unknown Error: {err}", stack_info=True)

        logger.warning(f"Timestream Handler: Drop: {result}")


class TimeStreamReader:
    def __init__(self):
        self.status = None

        try:
            self.reader = boto3.client("timestream-query", region_name=REGION)
            self.paginator = self.reader.get_paginator("query")
        except Exception as err:
            logger.exception(f"Timestream Handler: Could not connect to Timestream: Unknown Error: {err}", stack_info=True)

            self.status = {"statusCode": 503, "body": {"message": "[Service Unavailable] Timestream database is unreachable"}}

    def parse_rows(self, column_info: list, rows: list) -> list:
        # TODO: This method can be made static
        row_results: list = []
        for row in rows:
            data = row["Data"]
            row_output = {}
            for j in range(len(data)):
                datum = data[j]
                info = column_info[j]
                try:
                    row_output[info["Name"]] = datum.get("ScalarValue")
                except KeyError:
                    logger.warning(f"Timestream Handler: {datum} has no key!")
            row_results.append(row_output)
        return row_results
    
Time_Series_Writer = TimeStreamWriter()
Time_Series_Reader = TimeStreamReader()
    
def generate_client_token():
    token = "".join(random.choices(string.ascii_lowercase + string.digits, k=32))

    return token


def timestream_record(dimensions: dict, measure_name: str, measure_value, measure_type: str, time=None) -> dict:
    """
    Constructs a dictionary representing a single record for a timeseries database table.

    Args:
        dimensions (dict): A dictionary containing the dimensions for the record.
        measure_name (str): The name of the measure for the record.
        measure_value: The value of the measure for the record.
        measure_type (str): The type of the measure for the record.
        time (Optional[int]): The timestamp for the record. If not provided, the current time is used.

    Returns:
        dict: A dictionary representing a single record for a timeseries database table.
    """

    ts_dimensions: list = []
    for name, value in dimensions.items():
        try:
            ts_dimensions.append({"Name": name, "Value": value})
        except ValueError as err:
            logger.error(f"DB Interface: Timeseries Record: {err} on {dimensions}")

            return {}

    record = {
        "Dimensions": ts_dimensions,
        "MeasureName": measure_name,
        "MeasureValue": str(measure_value),
        "MeasureValueType": measure_type.upper(),
    }

    if not time:
        record["Time"] = str(int(round(datetime.utcnow().timestamp() * 1000)))
    else:
        record["Time"] = str(time)
    record["TimeUnit"] = "MILLISECONDS"

    return record


@xray_recorder.capture("Timestream")  # type: ignore
def timeseries_add_item(table, records: list):
    """Add a point or points in the table"""

    logger.debug(f"DB Interface: Timeseries single item action: Table: {table} Records: {records}")

    try:
        logger.info(f"DB Interface: Timeseries Writer: {records}")
        Time_Series_Writer.writer.write_records(DatabaseName=DATABASE_NAME, TableName=table.value.lower(), Records=records)
    except Time_Series_Writer.writer.exceptions.RejectedRecordsException as err:
        logger.warning(f"DB Interface: Timeseries RejectedRecords: Table: {table} Error: {err}")
        for rr in err.response["RejectedRecords"]:
            logger.info(f"DB Interface: Timeseries Rejected Index {rr['RecordIndex']} : {rr['Reason']}")
        logger.debug("DB Interface: Timeseries Other records were written successfully.")
    except Exception as err:
        logger.exception(f"DB Interface: Timeseries {err}", stack_info=True)


@xray_recorder.capture("Timestream")  # type: ignore
def timeseries_add_batch(table, records: list, common_attributes=None) -> None:
    """
    Writes a batch of records to a timeseries database table.

    Args:
        table (Table): The name of the database table to write the records to.
        records (list): A list of dictionaries, each representing a single record to be written to the table.
        common_attributes (Optional[dict]): A dictionary containing common attributes for all records in the batch.

    Returns:
        None.
    """

    if not records:
        logger.info(f"DB Interface: Timeseries No Records Transmitted - Table {table}")
        return

    logger.debug(f"DB Interface: Timeseries Record Count {len(records)} - Table {table}")

    record_count = len(records)

    if record_count <= TS_PAGE_SIZE:
        write_args = {
            k: v
            for k, v in {
                "Records": records,
                "CommonAttributes": common_attributes,
            }.items()
            if v
        }

        Time_Series_Writer.write_records(write_args, table)
    else:
        blocks = record_count // TS_PAGE_SIZE
        short = record_count % TS_PAGE_SIZE

        for i in range(blocks):
            write_args = {
                k: v
                for k, v in {
                    "Records": records[i * TS_PAGE_SIZE : (i + 1) * TS_PAGE_SIZE],
                    "CommonAttributes": common_attributes,
                }.items()
                if v
            }

            Time_Series_Writer.write_records(write_args, table)

        if short > 0:
            write_args = {
                k: v
                for k, v in {
                    "Records": records[blocks * TS_PAGE_SIZE : (blocks * TS_PAGE_SIZE) + short],
                    "CommonAttributes": common_attributes,
                }.items()
                if v
            }

            Time_Series_Writer.write_records(write_args, table)


@xray_recorder.capture("Timestream")  # type: ignore
def timeseries_query(query: str, token=None) -> list:
    logger.debug(f"DB Interface: Timeseries Single Page Query: Query: {query}")

    if not token:
        token = generate_client_token()

    results: list = []
    column_info: list = []

    try:
        query_result = Time_Series_Reader.reader.query(
            QueryString=query,
            ClientToken=token,
        )
        results.extend(query_result["Rows"])
        column_info.extend(query_result["ColumnInfo"])

        logger.debug(f"DB Interface: Timeseries Single Page Query: Results: {results}")

        if not results:
            logger.info(f"DB Interface: Timeseries Single Page Query: No Results: Query: {query}")

        parsed_results = Time_Series_Reader.parse_rows(column_info, results)

        return parsed_results

    except Exception as err:
        logger.exception(f"DB Interface: Timeseries Exception while running query: {query} Error: {err}", stack_info=True)

        raise Exception from err


@xray_recorder.capture("Timestream")  # type: ignore
def timeseries_long_query(
    query: str,
    next_token=None,
    token=None,
) -> list:
    logger.debug(f"DB Interface: Timeseries Performing paginated query: {query}, {next_token}")

    if not token:
        token = generate_client_token()

    results: list = []
    column_info: list = []

    query_args = {k: v for k, v in ({"QueryString": query, "NextToken": next_token}).items() if v}

    try:
        page_iterator = Time_Series_Reader.paginator.paginate(**query_args)
        for page in page_iterator:
            results += page["Rows"]
            column_info += page["ColumnInfo"]
        return Time_Series_Reader.parse_rows(column_info, results)
    except Exception as err:
        logger.exception(f"DB Interface: Timeseries Exception while running query.{err}", stack_info=True)

    return []

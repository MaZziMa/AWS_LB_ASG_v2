import json
import os
import time
import boto3
from botocore.exceptions import ClientError

TABLE_NAME = os.environ.get("ADMISSIONS_TABLE", "hutech-admissions")
SAMPLE_DATA_PATH = os.environ.get("SAMPLE_DATA_PATH", "../sample_data.json")
REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))


def ensure_table(dynamodb_client):
    try:
        dynamodb_client.describe_table(TableName=TABLE_NAME)
        return
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    print(f"Creating table {TABLE_NAME}...")
    dynamodb_client.create_table(
        TableName=TABLE_NAME,
        AttributeDefinitions=[{"AttributeName": "program_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "program_id", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )

    waiter = dynamodb_client.get_waiter("table_exists")
    waiter.wait(TableName=TABLE_NAME)
    print("Table created.")


def chunked(items, chunk_size):
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]


def main():
    session = boto3.Session(region_name=REGION)
    dynamodb = session.resource("dynamodb")
    dynamodb_client = session.client("dynamodb")

    ensure_table(dynamodb_client)

    table = dynamodb.Table(TABLE_NAME)

    sample_path = os.path.normpath(os.path.join(os.path.dirname(__file__), SAMPLE_DATA_PATH))
    with open(sample_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not isinstance(items, list) or not items:
        raise ValueError("sample_data.json must be a non-empty JSON array")

    print(f"Importing {len(items)} items into {TABLE_NAME}...")

    with table.batch_writer(overwrite_by_pkeys=["program_id"]) as batch:
        for item in items:
            batch.put_item(Item=item)

    print("Import completed.")


if __name__ == "__main__":
    main()

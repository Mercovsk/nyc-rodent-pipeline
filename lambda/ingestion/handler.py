import boto3
import json
import logging
import os
import time
import urllib.parse
import urllib.request

from botocore.exceptions import ClientError
from datetime import datetime, timedelta

# ====================
# ENV VARIABLES
# ====================
API_TOKEN = os.environ.get('API_TOKEN')
BASE_URL = 'https://data.cityofnewyork.us/api/v3/views/p937-wjvj/query.json'
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", 1000))
BUCKET_NAME = os.environ.get("S3_BUCKET")
DDB_TABLE = os.environ.get("DDB_TABLE")
PIPELINE_PK = "RODENT_PIPELINE"
SLIDING_WINDOW_DAYS = os.environ.get("SLIDING_WINDOW_DAYS", 0)

# ====================
# AWS Clients
# ====================
s3 = boto3.client('s3')
dynamodb = boto3.client("dynamodb")
logging.getLogger().setLevel(logging.INFO)

# ====================
# Helper Functions
# ====================

def get_watermark():
    response = dynamodb.get_item(
        TableName=DDB_TABLE,
        Key={
            "PK": {"S": PIPELINE_PK}
        }
    )

    if "Item" not in response:
        return{
            "last_created_at": "1970-01-01T00:00:00.000",
            "last_id": None,
            "status": "HISTORICAL_RUNNING"
        }

    item = response["Item"]
    return {
        "last_created_at": item['last_created_at']['S'],
        "last_id": item['last_id']['S'],
        "status": item.get("status", {}).get('S', 'HISTORICAL_RUNNING')
    }

def update_watermark(old_created_at, old_id, new_created_at, new_id, status=None):
    update_expr = """
        SET last_created_at = :new_created_at,
            last_id = :new_id,
            updated_at = :now
    """
    
    expr_value = {
        ":new_created_at": {'S': new_created_at},
        ":new_id": {'S': str(new_id)},
        ":now": {'S': datetime.utcnow().isoformat()}
    }

    if status:
        update_expr += ", #s = :status"
        expr_value[":status"] = {'S': status}

    try:
        params = {
            "TableName": DDB_TABLE,
            "Key": {
                "PK": {'S': PIPELINE_PK}
            },
            "UpdateExpression": update_expr,
            "ConditionExpression": "last_created_at = :old_created_at AND last_id = :old_id" if old_id else "last_created_at = :old_created_at",
            "ExpressionAttributeValues":{
                **expr_value,
                ":old_created_at": {'S': old_created_at},
                ":old_id": {'S': old_id} if old_id else None
            }
        }

        # Remove None keys from ExpressionAttributeValues
        params["ExpressionAttributeValues"] = {k: v for k, v in params["ExpressionAttributeValues"].items() if v is not None}

        # Only add ExpressionAttributeNames if status exists
        if status:
            params["ExpressionAttributeNames"] = {"#s": "status"}
        
        dynamodb.update_item(**params)

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise Exception("Watermark conflict detected. Possible concurrent execution.")
        raise

def build_query(last_created_at, last_id=None):
    if last_id:
        query = f"""
            SELECT *
            WHERE (:created_at > '{last_created_at}')
                OR
                (:created_at = '{last_created_at}' AND :id > '{last_id}')
            ORDER BY :created_at, :id
            LIMIT {BATCH_SIZE}
        """
    else:
        query = f"""
            SELECT *
            WHERE (:created_at > '{last_created_at}')
            ORDER BY :created_at, :id
            LIMIT {BATCH_SIZE}
        """

    encoded_query = urllib.parse.quote(query)

    return f"{BASE_URL}?app_token={API_TOKEN}&query={encoded_query}"

def fetch_batch(url, max_retries=5):
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            # req.add_header("X-App-Token", API_TOKEN)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())

        except urllib.error.HTTPError as e:
            error_body = e.read().decode()

            # Try to parse Socrata JSON error
            try:
                error_json = json.loads(error_body)
                logging.error(f"Socrata API Error: {error_body}")
            except:
                logging.error(f"HTTP Error {e.code}: {error_body}")

            # Do NOT retry 4xx client errors
            if 400 < e.code < 500:
                raise Exception(f"Client error from Socrata: {error_body}")

            # Retry only 5xx
            sleep_time = 2 ** attempt
            logging.warning(f"Server error {e.code}, retrying in {sleep_time}s")
            time.sleep(sleep_time)

        except Exception as e:
            sleep_time = 2 ** attempt
            logging.warning(f"API error, retrying in {sleep_time}s: {e}")
            time.sleep(sleep_time)
    
    raise Exception("Max retries exceed while fetching Socrata data.")

def write_to_s3(records, max_created_at, max_id):
    if not records:
        return

    dt = datetime.fromisoformat(max_created_at.replace('Z', ''))
    key = (
        f"raw/"
        f"year={dt.year}/"
        f"month={dt.month:02d}/"
        f"day={dt.day:02d}/"
        f"batch_{max_created_at}_{max_id}.json"
    )

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json.dumps(records),
        ContentType="application/json"
    )

def applying_sliding_window(created_at):
    if int(SLIDING_WINDOW_DAYS) <= 0:
        return created_at

    dt = datetime.fromisoformat(created_at.replace('Z',''))
    dt -= timedelta(days=SLIDING_WINDOW_DAYS)
    return  dt.isoformat()

# ====================
# Lambda Handler
# ====================

def lambda_handler(event, context):
    logging.info("Starting ingestion run")

    watermark = get_watermark()
    last_created_at = watermark["last_created_at"]
    last_id = watermark["last_id"]

    # Optional sliding window
    query_created_at = applying_sliding_window(last_created_at)

    while True:
        query_url = build_query(query_created_at, last_id)
        logging.info(f"Fetching batch from: {query_url}")

        records = fetch_batch(query_url)

        if not records:
            logging.info("No more records found.")
            if watermark["status"] == "HISTORICAL_RUNNING":
                update_watermark(
                    last_created_at,
                    last_id,
                    last_created_at,
                    last_id,
                    status="COMPLETE"
                )
            break
        
        max_record = records[-1]
        max_created_at = max_record[':created_at']
        max_id = max_record[':id']

        # Safety guard to prevent infinite loop
        if max_created_at == last_created_at and max_id == last_id:
            logging.warning("Watermark did not advance. Breaking loop.")
            break

        # Write batch to S3
        write_to_s3(records, max_created_at, max_id)

        # Advance watermark AFTER successful S3 write
        update_watermark(
            last_created_at,
            last_id,
            max_created_at,
            max_id
        )

        # Move forward
        last_created_at = max_created_at
        last_id = max_id
        query_created_at = max_created_at

        if len(records) < BATCH_SIZE:
            logging.info("Final batch processed.")

    logging.info("Ingestion complete")
    return {"status": "SUCCESS"}
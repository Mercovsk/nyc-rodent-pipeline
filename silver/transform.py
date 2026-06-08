import json
import logging
import os
from pathlib import Path

from silver.db import get_db_connection
from silver.models import Inspection
from pydantic import ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_json(filepath: str) -> list:
    with open(filepath, "r") as f:
        return json.load(f)

def upsert_record(cur, record: Inspection) -> None:
    cur.execute("""
        INSERT INTO inspections (
                socrata_id,
                inspection_type,
                borough,
                zip_code,
                inspection_date,
                result,
                approved_date,
                latitude,
                longitude,
                nta,
                community_board,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (socrata_id)
                DO UPDATE SET
                    inspection_type = EXCLUDED.inspection_type,
                    borough         = EXCLUDED.borough,
                    zip_code        = EXCLUDED.zip_code,
                    inspection_date = EXCLUDED.inspection_date,
                    result          = EXCLUDED.result,
                    approved_date   = EXCLUDED.approved_date,
                    latitude        = EXCLUDED.latitude,
                    longitude       = EXCLUDED.longitude,
                    nta             = EXCLUDED.nta,
                    community_board = EXCLUDED.community_board,
                    created_at      = EXCLUDED.created_at,
                    updated_at      = EXCLUDED.updated_at
                WHERE inspections.updated_at < EXCLUDED.updated_at
        """, (
            record.socrata_id,
            record.inspection_type,
            record.borough,
            record.zip_code,
            record.inspection_date,
            record.result,
            record.approved_date,
            record.latitude,
            record.longitude,
            record.nta,
            record.community_board,
            record.created_at,
            record.updated_at
        ))

def process_file(filepath: str) -> None:
    raw_records = load_json(filepath)
    inserted = 0
    errors = 0

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for raw in raw_records:
                try:
                    record = Inspection.model_validate(raw)
                    upsert_record(cur, record)
                    inserted += 1
                except ValidationError as e:
                    logger.error(f"Validation failed for {raw.get(':id')}: {e}")
                    errors += 1
                except Exception as e:
                    logger.error(f"DB error for {raw.get(':id')}: {e}")
                    conn.rollback()
                    errors += 1

        conn.commit()
    
    logger.info(f"Done - inserted/updated: {inserted}, errors: {errors}")

def process_directory(directory: str) -> None:
    json_files = list(Path(directory).glob("*.json"))

    if not json_files:
        logger.warning(f"No JSON files found in {directory}")

    logger.info(f"Found {len(json_files)} files to process.")

    for filepath in json_files:
        logger.info(f"Processing {filepath.name}")
        process_file(str(filepath))

if __name__ == "__main__":
    directory = os.path.join(Path(__file__).parent.parent, "data")
    process_directory(directory)

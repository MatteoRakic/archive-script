from datetime import datetime, timedelta

import boto3
import polars as pl
from logger import logger

cnt = 0

s3_client = boto3.client("s3")


srn_to_load = "decrypted-sorted-srn"

from consts import *

def list_all_keys(bucket):
    keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    # pages = paginator.paginate(Bucket=bucket,Prefix=prefix,PaginationConfig={'MaxItems': 10})
    pages = paginator.paginate(Bucket=bucket, Prefix=SOURCE_PREFIX)

    for page in pages:
        if "Contents" in page:
            for obj in page["Contents"]:
                if obj["Key"] != SOURCE_PREFIX + "/":
                    keys.append(
                        (obj["Key"], obj["LastModified"].strftime("%Y-%m-%dT%H:%M:%SZ"))
                    )

    return keys


# Fetch all object keys
all_keys = list_all_keys(S3_BUCKET)

df = pl.DataFrame(schema={"key_filename": pl.Utf8, "Date": pl.Utf8}, data=all_keys)

# Convert Date column from string to datetime
df = df.with_columns(pl.col("Date").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%SZ"))

# Test for files older than 10 minutes
df_archive = df.filter(
    pl.col("Date") < datetime.now() - timedelta(minutes=TEST_MAX_FILE_AGE_IN_MINS)
)

# Test for files older than 10 Days
df_archive = df.filter(
    pl.col("Date") < datetime.now() - timedelta(days=MAX_FILE_AGE_IN_DAYS)
)

if len(df_archive) == 0:
    logger.info("No files to archive")
else:
    logger.info(f"Found {len(df_archive)} files to archive:")

# Move files from source to target prefix
for row in df_archive.iter_rows(named=True):
    source_key = row["key_filename"]
    key_filename = source_key.replace(f"{SOURCE_PREFIX}/", "")
    target_key = f"{TARGET_PREFIX}/{key_filename}"

    try:
        # Copy object to target location
        s3_client.copy_object(
            Bucket=S3_BUCKET,
            CopySource={"Bucket": S3_BUCKET, "Key": source_key},
            Key=target_key,
        )
        logger.info(f"Successfully copied {source_key} to {target_key}")

        # Delete original object (completing the "move")
        s3_client.delete_object(Bucket=S3_BUCKET, Key=source_key)
        logger.info(f"Successfully deleted {source_key}")

    except Exception as e:
        logger.error(f"Error moving file {source_key}: {str(e)}")

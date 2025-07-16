import argparse
import time
from datetime import datetime, timedelta

import boto3
import polars as pl

from consts import (
    MAX_FILE_AGE_IN_DAYS,
    S3_BUCKET,
    SOURCE_PREFIX,
    TARGET_PREFIX,
)

# from consts import (
#     TEST_BUCKET,
#     TEST_MAX_FILE_AGE_IN_MINS,
#     TEST_SOURCE_PREFIX,
#     TEST_TARGET_PREFIX,
# )
from logger import logger

s3_client = boto3.client("s3")


def list_all_keys(bucket, file_type):
    keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    # pages = paginator.paginate(Bucket=bucket,Prefix=prefix,PaginationConfig={'MaxItems': 10})
    pages = paginator.paginate(Bucket=bucket, Prefix=SOURCE_PREFIX)

    for page in pages:
        if "Contents" in page:
            for obj in page["Contents"]:
                if obj["Key"] != SOURCE_PREFIX + "/":
                    key = obj["Key"]
                    filename = key.replace(SOURCE_PREFIX + "/", "")
                    filename = filename.replace(".", "_")
                    srn = filename.split("_")[0]
                    if file_type != "MA" and "CBA" not in filename:
                        file_date_year = filename.split("_")[4][:4]
                        file_date_month = filename.split("_")[4][4:6]
                    else:
                        file_date_year = filename.split("_")[1][:4]
                        file_date_month = filename.split("_")[1][4:6]
                    keys.append(
                        (
                            key,
                            srn,
                            obj["LastModified"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                            file_date_year,
                            file_date_month,
                        )
                    )

    return keys


# Start timer
argparser = argparse.ArgumentParser()
argparser.add_argument(
    "--file_type", type=str, default="all", help="File type to archive"
)
args = argparser.parse_args()
ft = args.file_type

timer = time.time()

# Fetch all object keys
all_keys = list_all_keys(S3_BUCKET, ft)

df = pl.DataFrame(
    schema={
        "key_filename": pl.Utf8,
        "srn": pl.Utf8,
        "last_modified_date": pl.Utf8,
        "file_date_year": pl.Utf8,
        "file_date_month": pl.Utf8,
    },
    data=all_keys,
    orient="row",
)

# Convert Date column from string to datetime
df = df.with_columns(
    pl.col("last_modified_date").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%SZ")
)

# Test for files older than 1 minutes
# df_archive = df.filter(
#     pl.col("last_modified_date")
#     < datetime.now() - timedelta(minutes=TEST_MAX_FILE_AGE_IN_MINS)
# )

# Test for files older than 10 Days
df_archive = df.filter(
    pl.col("Date") < datetime.now() - timedelta(days=MAX_FILE_AGE_IN_DAYS)
)

if len(df_archive) == 0:
    logger.info("No files to archive")
else:
    logger.info("Found %d files to archive:", len(df_archive))

# Move files from source to target prefix
for row in df_archive.iter_rows(named=True):
    source_key = row["key_filename"]
    print(source_key)
    srn = row["srn"]
    effective_year_month = f"{row['file_date_year']}-{row['file_date_month']}"
    key_filename = source_key.replace(f"{SOURCE_PREFIX}/", "")
    target_key = f"{TARGET_PREFIX}/supplier-reference-number={srn}/effective-year-month={effective_year_month}/{key_filename}"
    try:
        # Copy object to target location
        response = s3_client.copy_object(
            Bucket=S3_BUCKET,
            CopySource={"Bucket": S3_BUCKET, "Key": source_key},
            Key=target_key,
        )

        s3_status = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        if s3_status == 200:
            logger.info("Successfully copied %s to %s", {source_key}, {target_key})
            # Delete original object (completing the "move")
            s3_client.delete_object(Bucket=S3_BUCKET, Key=source_key)
            logger.info("Successfully deleted %s", {source_key})
        else:
            logger.error("Failed to copy %s to %s", {source_key}, {target_key})

    except Exception as e:
        logger.error("Error moving file %s: %s", {source_key}, {str(e)})

# End timer and log elapsed time
elapsed_time = time.time() - timer
logger.info("Script completed in %d seconds", elapsed_time)

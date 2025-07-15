from datetime import datetime, timedelta

import boto3
import polars as pl

cnt = 0

s3_client = boto3.client("s3")


srn_to_load = "decrypted-sorted-srn"


S3_BUCKET = "artemis-int-ingestion-files-af-south-1-992382549029"
TARGET_PREFIX = "workstage=landing-archive"
SOURCE_PREFIX = "workstage=landing"
MAX_FILE_AGE_IN_DAYS = "10"

TEST_BUCKET = "neil-992382549029"
TEST_TARGET_PREFIX = "matt_archived"
TEST_SOURCE_PREFIX = "matt_old"
TEST_MAX_FILE_AGE_IN_MINS = 10


def list_all_keys(bucket):
    keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    # pages = paginator.paginate(Bucket=bucket,Prefix=prefix,PaginationConfig={'MaxItems': 10})
    pages = paginator.paginate(Bucket=bucket, Prefix=TEST_SOURCE_PREFIX)

    for page in pages:
        if "Contents" in page:
            for obj in page["Contents"]:
                if obj["Key"] != TEST_SOURCE_PREFIX + "/":
                    keys.append(
                        (obj["Key"], obj["LastModified"].strftime("%Y-%m-%dT%H:%M:%SZ"))
                    )

    return keys


# Fetch all object keys
all_keys = list_all_keys(TEST_BUCKET)

df = pl.DataFrame(schema={"key_filename": pl.Utf8, "Date": pl.Utf8}, data=all_keys)

# Convert Date column from string to datetime
df = df.with_columns(pl.col("Date").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%SZ"))

df_archive = df.filter(
    pl.col("Date") < datetime.now() - timedelta(minutes=TEST_MAX_FILE_AGE_IN_MINS)
)

if len(df_archive) == 0:
    print("No files to archive")
else:
    print(f"Found {len(df_archive)} files to archive:")

# Move files from source to target prefix
for row in df_archive.iter_rows(named=True):
    source_key = row["key_filename"]
    key_filename = source_key.replace(f"{TEST_SOURCE_PREFIX}/", "")
    target_key = f"{TEST_TARGET_PREFIX}/{key_filename}"

    try:
        # Copy object to target location
        s3_client.copy_object(
            Bucket=TEST_BUCKET,
            CopySource={"Bucket": TEST_BUCKET, "Key": source_key},
            Key=target_key,
        )
        print(f"Successfully copied {source_key} to {target_key}")

        # Delete original object (completing the "move")
        s3_client.delete_object(Bucket=TEST_BUCKET, Key=source_key)
        print(f"Successfully deleted {source_key}")

    except Exception as e:
        print(f"Error moving file {source_key}: {str(e)}")

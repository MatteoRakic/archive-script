import boto3
import os
import pandas as pd

cnt=0

s3_client = boto3.client('s3')


srn_to_load='decrypted-sorted-srn'


S3_BUCKET="s3://artemis-int-ingestion-files-af-south-1-992382549029"
TARGET_PREFIX="workstage=landing-archive"
SOURCE_PREFIX="workstage=landing"
MAX_FILE_AGE_IN_DAYS="10"

def list_all_keys(bucket):
    keys = []
    paginator = s3_client.get_paginator('list_objects_v2')
    #pages = paginator.paginate(Bucket=bucket,Prefix=prefix,PaginationConfig={'MaxItems': 10})
    pages = paginator.paginate(Bucket=bucket,Prefix=SOURCE_PREFIX)

    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                #if any(srn in obj['Key'] for srn in srn_list):
                keys.append(obj['Key'])

    return keys

print(list_all_keys(S3_BUCKET))

# Fetch all object keys
all_keys = list_all_keys(S3_BUCKET)

df = pd.DataFrame(columns=["SRN", "A", "Evo", "Type", "Date","file_count", "file_seq","file_path"])
print('all keys')

for key in all_keys:
    print(key)
    filenamefull=os.path.basename(key)
    filename = filenamefull.replace(".txt", "")
    fields = filename.split("_")
    fields.append(f"{bucket_name}/{key}")

    try:
        df.loc[cnt] = fields
        cnt=cnt+1
     
    except:
        #append filename to an array
        failed_files.append(filename)
 

df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d', errors='coerce')  
   
  # Sort dataframe by Date and file_seq columns
df_filtered = df[(df['Type'].isin(file_type_list)) & (df['Date'] >= date_process_from)]
#df_filtered = df[df['SRN'].isin(['AB0103', 'TK0004', 'XB0177', 'IV0104', 'WS0106'])]
df_sorted = df_filtered.sort_values(['Date', 'file_seq'])


  # Loop through sorted dataframe and execute S3 copy operations
for index, row in df_sorted.iterrows():
    try:
        source_key = row['file_path']#.replace(bucket_name,'')  
        filename = os.path.basename(source_key)
        date_str = row['Date'].strftime('%Y%m%d')
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}" if len(date_str) >= 8 else "unknown-date"
        target_key = f"{sorted_prefix}/{row['SRN']}/{formatted_date}/{filename}"  # Create new key with SRN prefix
        
        # Execute S3 copy
        s3_client.copy_object(
            Bucket=bucket_name,
            CopySource=source_key,
            Key=target_key
        )
        print(f"Successfully copied {source_key} to {target_key}")
        
    except Exception as e:
        print(f"Error copying file {row['file_path']}: {str(e)}")
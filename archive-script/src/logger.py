import logging

logging.basicConfig(level="INFO")

logger = logging.getLogger("ARCHIVER")

logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)

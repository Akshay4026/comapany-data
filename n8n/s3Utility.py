from dotenv import load_dotenv
load_dotenv()

import boto3
import os

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")  # fixed typo
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
Bucket_Name = "companies-json-files"

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def upload_file(file_path, file_name):
    s3.upload_file(file_path, Bucket_Name, file_name)
    print(f"File uploaded successfully: s3://{Bucket_Name}/{file_name}")

def download_file_from_s3(s3_key, file_path):
    s3.download_file(Bucket_Name, s3_key, file_path)
    print(f"Downloaded s3://{Bucket_Name}/{s3_key} → {file_path}")

def read_file_from_s3(s3_key):
    response = s3.get_object(Bucket=Bucket_Name, Key=s3_key)
    return response['Body'].read().decode("utf-8")

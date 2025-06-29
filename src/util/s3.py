import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

class S3Client:
    def __init__(self, bucket_name):
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name
        
    
    def generate_presigned_url(self, key, content_type, expiration=3600):
        return self.s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': key,
                'ContentType': content_type,
            },
            ExpiresIn=expiration
        )
        
    def get_s3_file(self, key):
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read().decode('utf-8')
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"The file {key} does not exist in bucket {self.bucket_name}.")
            else:
                raise Exception(f"An error occurred while retrieving the file: {str(e)}")  

           
s3_client = S3Client(bucket_name=BUCKET_NAME)                
def get_s3_client():
    if not BUCKET_NAME:
        raise ValueError("AWS_BUCKET_NAME environment variable is not set.")
    return s3_client            
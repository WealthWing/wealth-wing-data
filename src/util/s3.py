import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

class S3Client:
    """
    S3Client provides utility methods to interact with an AWS S3 bucket.
    Attributes:
        s3_client (boto3.client): The boto3 S3 client instance.
        bucket_name (str): The name of the S3 bucket to interact with.
    Methods:
        __init__(bucket_name):
            Initializes the S3Client with the specified S3 bucket name.
        generate_presigned_url(key, content_type, expiration=3600):
            Generates a presigned URL to upload a file to S3 with the given key and content type.
            Args:
                key (str): The S3 object key (file path in the bucket).
                content_type (str): The MIME type of the file to be uploaded.
                expiration (int, optional): Time in seconds for the presigned URL to remain valid. Defaults to 3600.
            Returns:
                str: A presigned URL for uploading the file.
        get_s3_file(key):
            Retrieves the contents of a file from S3 as a UTF-8 decoded string.
            Args:
                key (str): The S3 object key (file path in the bucket).
            Returns:
                str: The contents of the file.
            Raises:
                FileNotFoundError: If the specified file does not exist in the bucket.
                Exception: For other errors encountered during retrieval.
    """
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
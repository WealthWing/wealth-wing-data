import boto3

def generate_presigned_url(bucket, key, content_type, expiration=3600):
    s3_client = boto3.client('s3')
    return s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': bucket,
            'Key': key,
            'ContentType': content_type,
        },
        ExpiresIn=expiration
    )

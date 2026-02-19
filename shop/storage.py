import boto3
import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_s3_client():
    """Get S3-compatible client for R2/S3 storage."""
    if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.R2_ENDPOINT]):
        logger.warning("R2/S3 storage not configured")
        return None
    
    return boto3.client(
        's3',
        endpoint_url=settings.R2_ENDPOINT,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name='auto'
    )


def generate_signed_url(file_key, expiration_hours=24):
    """Generate signed URL for digital download."""
    client = get_s3_client()
    if not client:
        return None
    
    try:
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.R2_BUCKET,
                'Key': file_key,
            },
            ExpiresIn=expiration_hours * 3600
        )
        return url
    except Exception as e:
        logger.error(f"Failed to generate signed URL: {e}")
        return None


def upload_file(file_obj, key):
    """Upload file to R2/S3 storage."""
    client = get_s3_client()
    if not client:
        return False
    
    try:
        client.upload_fileobj(file_obj, settings.R2_BUCKET, key)
        return True
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        return False


def delete_file(key):
    """Delete file from R2/S3 storage."""
    client = get_s3_client()
    if not client:
        return False
    
    try:
        client.delete_object(Bucket=settings.R2_BUCKET, Key=key)
        return True
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        return False
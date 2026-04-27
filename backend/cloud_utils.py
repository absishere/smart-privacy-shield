import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import NoCredentialsError
import hashlib

load_dotenv()

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=os.getenv("AWS_REGION")
)

BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

def upload_to_s3(file_path, object_name):
    """Uploads file to AWS S3 and returns a temporary Secure URL."""
    try:
        # 1. Upload the file
        s3_client.upload_file(str(file_path), BUCKET_NAME, object_name)
        
        # 2. Generate a Presigned URL (Valid for 15 minutes)
        # This ensures the data remains private on AWS, but accessible to our DApp
        url = s3_client.generate_presigned_url('get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': object_name},
            ExpiresIn=900) 
        
        print(f"✅ AWS S3: Uploaded {object_name}")
        return url
    except Exception as e:
        print(f"❌ AWS S3 Error: {e}")
        return None

def download_from_s3(object_name, download_path):
    """Downloads a file from S3 to a local temporary path for processing."""
    try:
        s3_client.download_file(BUCKET_NAME, object_name, str(download_path))
        print(f"✅ AWS S3: Downloaded {object_name} to {download_path}")
        return True
    except Exception as e:
        print(f"❌ AWS S3 Download Error: {e}")
        return False

def list_user_images(wallet_address):
    """Lists all encrypted/stego objects in S3 for a specific user."""
    if not wallet_address:
        return []
        
    try:
        files = []
        # List encrypted directory for this wallet
        response_enc = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f"encrypted/{wallet_address}/")
        if 'Contents' in response_enc:
            for obj in response_enc['Contents']:
                if obj['Key'].endswith(('.png', '.jpg', '.jpeg')):
                    files.append({
                        "key": obj['Key'],
                        "url": s3_client.generate_presigned_url('get_object', 
                            Params={'Bucket': BUCKET_NAME, 'Key': obj['Key']}, ExpiresIn=3600)
                    })
                    
        # List stego directory for this wallet
        response_stego = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f"stego/{wallet_address}/")
        if 'Contents' in response_stego:
            for obj in response_stego['Contents']:
                if obj['Key'].endswith(('.png', '.jpg', '.jpeg')):
                    files.append({
                        "key": obj['Key'],
                        "url": s3_client.generate_presigned_url('get_object', 
                            Params={'Bucket': BUCKET_NAME, 'Key': obj['Key']}, ExpiresIn=3600)
                    })
        return files
    except Exception as e:
        print(f"Error listing S3: {e}")
        return []

def get_s3_bytes(object_name: str) -> bytes | None:
    """Fetches file bytes directly from S3 into memory."""
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=object_name)
        return response['Body'].read()
    except Exception as e:
        print(f"❌ S3 Read Error for {object_name}: {e}")
        return None

def delete_from_s3(object_name: str) -> bool:
    """Permanently deletes a file from the S3 bucket."""
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_name)
        print(f"🗑️ AWS S3: Deleted {object_name}")
        return True
    except Exception as e:
        print(f"❌ AWS S3 Delete Error for {object_name}: {e}")
        return False

def recover_pristine_version(object_name: str, expected_hash: str) -> bytes | None:
    """Attempts to recover a clean version of the file from S3 using Object Versioning."""
    try:
        versions_response = s3_client.list_object_versions(Bucket=BUCKET_NAME, Prefix=object_name)
        versions = versions_response.get('Versions', [])
        
        for version in versions:
            version_id = version['VersionId']
            # Fetch this specific version
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=object_name, VersionId=version_id)
            file_bytes = response['Body'].read()
            
            # Calculate hash
            current_hash = hashlib.sha256(file_bytes).hexdigest()
            if current_hash == expected_hash:
                print(f"✅ S3 Self-Healing: Found pristine version (ID: {version_id})")
                
                # Perform permanent healing: copy this exact version over the current mutating object
                print("🔄 Starting permanent S3 healing copy...")
                copy_source = {
                    'Bucket': BUCKET_NAME,
                    'Key': object_name,
                    'VersionId': version_id
                }
                s3_client.copy_object(CopySource=copy_source, Bucket=BUCKET_NAME, Key=object_name)
                print(f"✅ S3 Self-Healing: Bucket permanently healed for {object_name}.")
                
                return file_bytes
                
        print(f"❌ S3 Self-Healing: No pristine version found matching hash for {object_name}.")
        return None
    except Exception as e:
        print(f"❌ S3 Self-Healing Error: {e}")
        return None

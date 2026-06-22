import os
import uuid
import oci
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ObjectStorageService:
    def __init__(self):
        self.bucket_name = os.getenv("OCI_BUCKET_NAME")
        self.namespace = os.getenv("OCI_NAMESPACE")
        self.region = os.getenv("OCI_REGION")
        try: 
            config = oci.config.from_file()
            self.client = oci.object_storage.ObjectStorageClient(config)
            logger.info("OCI Object Storage client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize OCI Object Storage client: {str(e)}")
            self.client = None

    def generate_object_name(self, folder: str, filename: str) -> str:
        """
        Generates a unique object name using UUID to prevent collisions.
        """
        extension = filename.split(".")[-1]
        return f"{folder}/{uuid.uuid4()}.{extension}"

    def upload_file(self, file_bytes: bytes, object_name: str, content_type: Optional[str] = None) -> str:
        """
        Uploads file bytes to the configured OCI bucket.
        Falls back to local file storage if OCI client is not initialized.
        """
        if not self.client:
            logger.warning("OCI client is not initialized. Falling back to local storage.")
            local_path = os.path.join("static", "uploads", "avatars", object_name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(file_bytes)
            logger.info(f"File saved locally to {local_path} as fallback.")
            return object_name
        
        logger.info(f"Uploading file to OCI bucket '{self.bucket_name}' as '{object_name}' with Content-Type '{content_type}'")
        try:
            kwargs = {}
            if content_type:
                kwargs['content_type'] = content_type
                
            self.client.put_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=object_name,
                put_object_body=file_bytes,
                **kwargs
            )
            logger.info("Upload completed successfully.")
            return object_name
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            raise e

    def delete_file(self, object_name: str):
        """
        Deletes an object from the OCI bucket or local fallback storage.
        """
        if not object_name:
            return

        if not self.client:
            local_path = os.path.join("static", "uploads", "avatars", object_name)
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    logger.info(f"Deleted old local avatar fallback file: {local_path}")
                except Exception as e:
                    logger.error(f"Failed to delete local avatar fallback file: {str(e)}")
            return

        logger.info(f"Deleting old OCI object '{object_name}' from bucket '{self.bucket_name}'")
        try:
            self.client.delete_object(
                namespace_name=self.namespace,
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            logger.info("Delete completed successfully.")
        except Exception as e:
            logger.error(f"Delete failed: {str(e)}")

    def generate_public_url(self, object_name: str) -> str:
        """
        Generates the public HTTP URL for the OCI object.
        """
        if not object_name:
            return ""
        return (
            f"https://objectstorage.{self.region}.oraclecloud.com"
            f"/n/{self.namespace}"
            f"/b/{self.bucket_name}"
            f"/o/{object_name}"
        )

    def get_public_url(self, object_name: Optional[str]) -> Optional[str]:
        """
        Returns the resolved public URL of any uploaded file/object.
        If it's None/empty, returns None.
        If it's already an absolute URL or a local static path, returns it as-is.
        If OCI client is not initialized, and the file exists locally, returns the local static URL.
        Otherwise, dynamically constructs and returns the OCI URL.
        """
        if not object_name:
            return None
        
        # If it starts with http, https, or /static/, return as is
        if object_name.startswith("http://") or object_name.startswith("https://") or object_name.startswith("/static/"):
            return object_name
            
        # If OCI client is not initialized, check if local fallback file exists
        if not self.client:
            local_path = os.path.join("static", "uploads", "avatars", object_name)
            if os.path.exists(local_path):
                # Replace backslashes with forward slashes for URLs
                return f"/static/uploads/avatars/{object_name.replace('\\', '/')}"
            
        # Otherwise, resolve as OCI Object name
        return self.generate_public_url(object_name)

    def get_public_avatar_url(self, avatar_val: Optional[str]) -> Optional[str]:
        """
        Returns the resolved public URL of an avatar.
        """
        return self.get_public_url(avatar_val)

# Instantiate a single service instance
storage_service = ObjectStorageService()

def extract_object_name(url: Optional[str]) -> Optional[str]:
    """
    Extracts the relative object name/path from a public URL.
    Returns None if the url is None/empty.
    """
    if not url:
        return None
    import urllib.parse
    # For local fallback URLs: /static/uploads/avatars/audio/uuid.aac
    if "static/uploads/avatars/" in url:
        raw_path = url.split("static/uploads/avatars/")[-1]
        return urllib.parse.unquote(raw_path)
    # For OCI public URLs: https://.../o/audio/uuid.aac
    if "/o/" in url:
        raw_path = url.split("/o/")[-1]
        return urllib.parse.unquote(raw_path)
    return url

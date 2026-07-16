"""Document storage abstraction (local/S3/Azure Blob)."""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base for document storage."""

    @abstractmethod
    async def upload(self, file_path: str, content: bytes) -> str:
        """Upload file and return storage path."""
        pass

    @abstractmethod
    async def download(self, file_path: str) -> bytes:
        """Download file content."""
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """Delete file."""
        pass

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """Check if file exists."""
        pass


class LocalStorage(StorageBackend):
    """Local filesystem storage (development)."""

    def __init__(self, base_path: str = "./data/uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalStorage initialized at {self.base_path}")

    async def upload(self, file_path: str, content: bytes) -> str:
        """Upload file to local storage."""
        full_path = self.base_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        logger.info(f"Uploaded {file_path} to local storage")
        return str(full_path)

    async def download(self, file_path: str) -> bytes:
        """Download file from local storage."""
        full_path = self.base_path / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"{file_path} not found")
        return full_path.read_bytes()

    async def delete(self, file_path: str) -> bool:
        """Delete file from local storage."""
        full_path = self.base_path / file_path
        if full_path.exists():
            full_path.unlink()
            logger.info(f"Deleted {file_path}")
            return True
        return False

    async def exists(self, file_path: str) -> bool:
        """Check if file exists in local storage."""
        return (self.base_path / file_path).exists()


class S3Storage(StorageBackend):
    """AWS S3 storage (production)."""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        try:
            import aioboto3

            self.bucket = bucket
            self.region = region
            self.session = aioboto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )
            logger.info(f"S3Storage initialized for bucket {bucket} in {region}")
        except ImportError:
            raise ImportError("aioboto3 required for S3 storage: pip install aioboto3")

    async def upload(self, file_path: str, content: bytes) -> str:
        """Upload file to S3."""
        async with self.session.client("s3", region_name=self.region) as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=file_path,
                Body=content,
            )
            logger.info(f"Uploaded {file_path} to S3")
            return f"s3://{self.bucket}/{file_path}"

    async def download(self, file_path: str) -> bytes:
        """Download file from S3."""
        async with self.session.client("s3", region_name=self.region) as s3:
            try:
                response = await s3.get_object(Bucket=self.bucket, Key=file_path)
                return await response["Body"].read()
            except Exception as e:
                logger.error(f"Failed to download {file_path} from S3: {e}")
                raise

    async def delete(self, file_path: str) -> bool:
        """Delete file from S3."""
        async with self.session.client("s3", region_name=self.region) as s3:
            try:
                await s3.delete_object(Bucket=self.bucket, Key=file_path)
                logger.info(f"Deleted {file_path} from S3")
                return True
            except Exception as e:
                logger.error(f"Failed to delete {file_path} from S3: {e}")
                return False

    async def exists(self, file_path: str) -> bool:
        """Check if file exists in S3."""
        async with self.session.client("s3", region_name=self.region) as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=file_path)
                return True
            except:
                return False


class AzureBlobStorage(StorageBackend):
    """Azure Blob Storage (production)."""

    def __init__(
        self,
        account_name: str,
        account_key: str,
        container: str = "documents",
    ):
        try:
            from azure.storage.blob.aio import BlobServiceClient

            self.container = container
            connection_string = (
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={account_name};"
                f"AccountKey={account_key};"
                f"EndpointSuffix=core.windows.net"
            )
            self.client = BlobServiceClient.from_connection_string(connection_string)
            logger.info(f"AzureBlobStorage initialized for {account_name}/{container}")
        except ImportError:
            raise ImportError(
                "azure-storage-blob required: pip install azure-storage-blob"
            )

    async def upload(self, file_path: str, content: bytes) -> str:
        """Upload file to Azure Blob."""
        try:
            blob_client = self.client.get_blob_client(
                container=self.container, blob=file_path
            )
            await blob_client.upload_blob(content, overwrite=True)
            logger.info(f"Uploaded {file_path} to Azure Blob")
            return f"azure://{self.container}/{file_path}"
        except Exception as e:
            logger.error(f"Failed to upload {file_path} to Azure Blob: {e}")
            raise

    async def download(self, file_path: str) -> bytes:
        """Download file from Azure Blob."""
        try:
            blob_client = self.client.get_blob_client(
                container=self.container, blob=file_path
            )
            download_stream = await blob_client.download_blob()
            return await download_stream.readall()
        except Exception as e:
            logger.error(f"Failed to download {file_path} from Azure Blob: {e}")
            raise

    async def delete(self, file_path: str) -> bool:
        """Delete file from Azure Blob."""
        try:
            blob_client = self.client.get_blob_client(
                container=self.container, blob=file_path
            )
            await blob_client.delete_blob()
            logger.info(f"Deleted {file_path} from Azure Blob")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {file_path} from Azure Blob: {e}")
            return False

    async def exists(self, file_path: str) -> bool:
        """Check if file exists in Azure Blob."""
        try:
            blob_client = self.client.get_blob_client(
                container=self.container, blob=file_path
            )
            return await blob_client.exists()
        except:
            return False


def get_storage() -> StorageBackend:
    """
    Factory function to get storage backend based on configuration.

    T-302: S3 client initialization (or local/Azure based on config)
    """
    storage_type = os.getenv("STORAGE_TYPE", "local").lower()

    if storage_type == "s3":
        return S3Storage(
            bucket=os.getenv("AWS_S3_BUCKET", "edgp-documents"),
            region=os.getenv("AWS_REGION", "us-east-1"),
            access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    elif storage_type == "azure":
        return AzureBlobStorage(
            account_name=os.getenv("AZURE_STORAGE_ACCOUNT_NAME", ""),
            account_key=os.getenv("AZURE_STORAGE_ACCOUNT_KEY", ""),
            container=os.getenv("AZURE_STORAGE_CONTAINER", "documents"),
        )

    else:  # local (default)
        return LocalStorage(
            base_path=os.getenv("STORAGE_LOCAL_PATH", "./data/uploads")
        )


# Global storage instance
_storage_instance: Optional[StorageBackend] = None


async def get_storage_instance() -> StorageBackend:
    """Get or create storage instance (singleton)."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = get_storage()
    return _storage_instance

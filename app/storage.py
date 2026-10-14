from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class StorageBackend(ABC):
    """Abstract storage interface allowing local filesystem deployment today

    and seamless migration to S3/MinIO without altering business logic.
    """

    @abstractmethod
    def store_bytes(self, relative_path: str, data: bytes) -> Path:
        """Store bytes at relative_path and return local or accessible path."""
        pass

    @abstractmethod
    def get_path(self, relative_path: str) -> Path:
        """Retrieve local filesystem path for a stored asset."""
        pass

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """Check if an asset exists."""
        pass

    @abstractmethod
    def get_public_url(self, run_id: str, asset_type: str, filename: str) -> str:
        """Return the public API URL to retrieve the asset."""
        pass


class LocalFilesystemStorage(StorageBackend):
    """Local server disk storage for campus deployments."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_bytes(self, relative_path: str, data: bytes) -> Path:
        target = (self.base_dir / relative_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def get_path(self, relative_path: str) -> Path:
        target = (self.base_dir / relative_path).resolve()
        if not target.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return target

    def exists(self, relative_path: str) -> bool:
        return (self.base_dir / relative_path).resolve().exists()

    def get_public_url(self, run_id: str, asset_type: str, filename: str) -> str:
        if asset_type == "audio":
            return f"/api/runs/{run_id}/audio/{filename}"
        elif asset_type == "image":
            return f"/api/runs/{run_id}/images/{filename}"
        elif asset_type == "video":
            return f"/api/runs/{run_id}/video/{filename}"
        return f"/api/runs/{run_id}/{asset_type}/{filename}"


class S3FilesystemStorage(StorageBackend):
    """Future S3 / MinIO storage adapter."""

    def __init__(self, bucket_name: str, endpoint_url: str | None = None):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url

    def store_bytes(self, relative_path: str, data: bytes) -> Path:
        # Placeholder for boto3 / aiobotocore client upload
        raise NotImplementedError("S3 storage will be activated when campus S3 bucket is provisioned.")

    def get_path(self, relative_path: str) -> Path:
        raise NotImplementedError("S3 storage direct path access is not applicable; use presigned URLs.")

    def exists(self, relative_path: str) -> bool:
        raise NotImplementedError("S3 exists check will be activated when campus S3 bucket is provisioned.")

    def get_public_url(self, run_id: str, asset_type: str, filename: str) -> str:
        return f"https://{self.bucket_name}.s3.amazonaws.com/{run_id}/{asset_type}/{filename}"

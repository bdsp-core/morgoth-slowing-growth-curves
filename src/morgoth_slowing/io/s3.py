"""S3 access to the BDSP credentialed bucket (docs/data_sources.md)."""
from __future__ import annotations


def inventory(prefix: str) -> "list[dict]":
    """List objects under an s3:// prefix with sizes. Phase 0 uses this to size the data
    and answer the disk-space question. Implement with boto3 or s3fs."""
    raise NotImplementedError("Phase 0")


def sync(prefix: str, local_dir: str) -> None:
    """Mirror an s3:// prefix to a local cache dir (or stream lazily via s3fs)."""
    raise NotImplementedError("Phase 0")

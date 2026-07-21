from functools import lru_cache
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.errors import AppError


def _local_path(key: str) -> Path:
    root = Path(get_settings().private_storage_dir).resolve()
    path = (root / key).resolve()
    if root not in path.parents:
        raise AppError(code="arquivo_invalido", message="Arquivo inválido.", status_code=500)
    return path


@lru_cache
def _s3_client() -> Any:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
    )


def put_bytes(key: str, content: bytes, content_type: str) -> None:
    settings = get_settings()
    if settings.uses_s3_storage:
        _s3_client().put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return
    target = _local_path(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def get_bytes(key: str) -> bytes:
    settings = get_settings()
    if settings.uses_s3_storage:
        try:
            response = _s3_client().get_object(Bucket=settings.s3_bucket, Key=key)
            return response["Body"].read()
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise AppError(
                    code="arquivo_nao_encontrado",
                    message="Arquivo não encontrado.",
                    status_code=404,
                ) from error
            raise
    path = _local_path(key)
    if not path.is_file():
        raise AppError(
            code="arquivo_nao_encontrado", message="Arquivo não encontrado.", status_code=404
        )
    return path.read_bytes()


def delete_bytes(key: str) -> None:
    settings = get_settings()
    if settings.uses_s3_storage:
        _s3_client().delete_object(Bucket=settings.s3_bucket, Key=key)
        return
    path = _local_path(key)
    path.unlink(missing_ok=True)

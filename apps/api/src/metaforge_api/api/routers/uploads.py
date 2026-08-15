from fastapi import APIRouter, UploadFile
from sqlalchemy import select

from metaforge_api.api.deps import CurrentUserDep, DbSession
from metaforge_api.infrastructure import storage
from metaforge_api.infrastructure.models import Upload
from metaforge_api.infrastructure.settings import settings

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("")
async def upload_file(file: UploadFile, session: DbSession, user: CurrentUserDep):
    content = await file.read()
    object_key = storage.put_object(file.filename, content, file.content_type or "application/octet-stream")
    upload = Upload(
        bucket=settings.s3_bucket,
        object_key=object_key,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        uploaded_by=user.id,
    )
    session.add(upload)
    await session.commit()
    return {"id": str(upload.id), "filename": upload.filename, "url": storage.presigned_get_url(object_key)}


@router.get("/{upload_id}")
async def get_upload_url(upload_id: str, session: DbSession, user: CurrentUserDep):
    row = (await session.execute(select(Upload).where(Upload.id == upload_id))).scalar_one_or_none()
    if row is None:
        return {"error": "not found"}
    return {"url": storage.presigned_get_url(row.object_key)}

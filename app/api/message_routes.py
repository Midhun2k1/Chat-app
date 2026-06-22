import os
from fastapi import APIRouter, UploadFile, File, Depends, Form
from app.auth.dependencies import get_current_user
from app.services.object_storage import storage_service
from app.schemas.response import StandardResponse
from app.utils.response_utils import success_response, error_response

router = APIRouter(prefix="/messages", tags=["messages"])

ALLOWED_CONTENT_TYPES = {
    "audio/aac", 
    "audio/mp4", 
    "audio/mpeg", 
    "audio/webm", 
    "audio/ogg", 
    "audio/x-aac", 
    "audio/wav", 
    "audio/x-wav"
}
MAX_SIZE_BYTES = int(os.getenv("MAX_AUDIO_SIZE_MB", "10")) * 1024 * 1024

@router.post("/upload-audio", response_model=StandardResponse[dict])
async def upload_audio_message(
    file: UploadFile = File(...),
    duration_seconds: int = Form(0, description="Duration of the audio in seconds"),
    current_user = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        return error_response(
            message=f"Unsupported content type: {file.content_type}. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}",
            code="UNSUPPORTED_MEDIA_TYPE",
            status_code=400
        )

    # Read contents to validate size
    contents = await file.read()
    if len(contents) > MAX_SIZE_BYTES:
        return error_response(
            message=f"File exceeds maximum allowed size of {MAX_SIZE_BYTES // (1024 * 1024)}MB",
            code="FILE_TOO_LARGE",
            status_code=400
        )

    try:
        # Determine extension
        ext = "aac"
        content_type_lower = file.content_type.lower()
        if "mp4" in content_type_lower:
            ext = "mp4"
        elif "mpeg" in content_type_lower or "mp3" in content_type_lower:
            ext = "mp3"
        elif "webm" in content_type_lower:
            ext = "webm"
        elif "ogg" in content_type_lower:
            ext = "ogg"
        elif "wav" in content_type_lower:
            ext = "wav"

        # Generate unique object name under the "audio" folder prefix
        object_name = storage_service.generate_object_name("audio", f"voice.{ext}")

        # Upload using the unified storage service
        storage_service.upload_file(contents, object_name, content_type=file.content_type)

        # Resolve public URL
        audio_url = storage_service.get_public_url(object_name)

        return success_response(
            data={
                "audio_url": audio_url,
                "duration_seconds": duration_seconds,
            },
            message="Audio uploaded successfully"
        )
    except Exception as e:
        return error_response(
            message=f"Failed to upload audio file: {str(e)}",
            code="UPLOAD_FAILED",
            status_code=500
        )

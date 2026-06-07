from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status
import os
import shutil
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from app.db.database import get_db
from app.db.models import User
from app.auth.dependencies import get_current_user
from app.schemas.user import UserSearchResponse, UserList, UserSearchRequest
from app.schemas.response import StandardResponse
from app.utils.response_utils import success_response
from app.services.object_storage import storage_service
from app.utils.image_utils import compress_image

router = APIRouter()


@router.post("/users", response_model=StandardResponse[UserList])
def get_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).filter(
        User.fld_user_id != current_user.fld_user_id
    ).all()

    users_list = [
        {
            "user_id": user.fld_user_id,
            "username": user.fld_username,
            "email": user.fld_email,
            "phone": user.fld_phone,
            "avatar_url": storage_service.get_public_avatar_url(user.fld_avatar_url)
        }
        for user in users
    ]

    return success_response(data={"users": users_list}, message="Users fetched successfully")


@router.post("/user-search", response_model=StandardResponse[UserList])
def search_users(
    request: UserSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    search_query = f"%{request.query}%"
    users = db.query(User).filter(
        User.fld_user_id != current_user.fld_user_id,
        or_(
            User.fld_username.ilike(search_query),
            User.fld_firstname.ilike(search_query),
            User.fld_lastname.ilike(search_query),
            (User.fld_firstname + " " + User.fld_lastname).ilike(search_query),
            User.fld_email.ilike(search_query)
        )
    ).limit(50).all()

    users_list = [
        {
            "user_id": user.fld_user_id,
            "username": user.fld_username,
            "firstname": user.fld_firstname,
            "lastname": user.fld_lastname,
            "email": user.fld_email,
            "phone": user.fld_phone,
            "avatar_url": storage_service.get_public_avatar_url(user.fld_avatar_url)
        }
        for user in users
    ]

    return success_response(data={"users": users_list}, message="Users fetched successfully")


import smtplib
from email.mime.text import MIMEText
import traceback

def send_debug_email_sync(to_email: str, subject: str, body: str):
    import os
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    
    if not smtp_user or not smtp_password:
        return
        
    msg = MIMEText(body)
    msg["Subject"] = f"[DEBUG] {subject}"
    msg["From"] = smtp_from
    msg["To"] = to_email
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_port == 587:
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, [to_email], msg.as_string())
    except Exception as e:
        print("Failed to send debug email:", e)

MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB
# We allow any content type starting with "image/"
ALLOWED_PREFIX = "image/"

@router.post("/users-avatar", response_model=StandardResponse[dict])
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    debug_logs = []
    
    def log_print(msg):
        print(msg)
        debug_logs.append(str(msg))

    try:
        log_print("--- Avatar Upload Request Started ---")
        log_print(f"User: {current_user.fld_username} ({current_user.fld_email})")
        log_print(f"File info: filename={file.filename}, content_type={file.content_type}")

        # 1. Validate File Content Type
        if not file.content_type or not file.content_type.startswith(ALLOWED_PREFIX):
            log_print("Validation Error: Invalid file type")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only image files are allowed."
            )

        # 2. Validate File Size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        log_print(f"File Size: {file_size} bytes")
        
        if file_size > MAX_FILE_SIZE:
            log_print(f"Validation Error: File size {file_size} exceeds max {MAX_FILE_SIZE}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is too large. Maximum size is 30MB."
            )

        # 3. Read image bytes and compress
        try:
            raw_bytes = file.file.read()
            compressed_bytes = compress_image(raw_bytes, file.content_type)
            log_print(f"Compression successful. Compressed size: {len(compressed_bytes)} bytes")
        except Exception as e:
            log_print(f"Compression Error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not process image: {str(e)}"
            )

        # 4. Delete old OCI object if user already has one to avoid orphans
        if current_user.fld_avatar_url:
            old_avatar = current_user.fld_avatar_url
            if not (old_avatar.startswith("http://") or old_avatar.startswith("https://") or old_avatar.startswith("/static/")):
                try:
                    storage_service.delete_file(old_avatar)
                    log_print(f"Deleted old avatar: {old_avatar}")
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Could not delete old avatar object '{old_avatar}': {str(e)}")
                    log_print(f"Warning deleting old avatar: {str(e)}")

        # 5. Generate unique object name and upload
        object_name = storage_service.generate_object_name("profile-photos", file.filename)
        try:
            storage_service.upload_file(compressed_bytes, object_name, content_type=file.content_type)
            log_print(f"Uploaded to OCI: {object_name}")
        except Exception as e:
            log_print(f"OCI Upload Error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload to OCI Object Storage: {str(e)}"
            )

        # 6. Save OCI object path in the database
        current_user.fld_avatar_url = object_name
        db.commit()
        db.refresh(current_user)
        log_print("Database updated successfully")

        # 7. Generate public URL dynamically to return to the client
        avatar_url = storage_service.get_public_avatar_url(object_name)
        log_print(f"Generated public avatar URL: {avatar_url}")

        # Send debug logs to email
        email_body = "\n".join(debug_logs) + "\n\nStatus: Success"
        send_debug_email_sync(current_user.fld_email, "Avatar Upload - Success Details", email_body)

        return success_response(
            data={"avatar_url": avatar_url},
            message="Profile picture uploaded successfully"
        )
        
    except HTTPException as he:
        email_body = "\n".join(debug_logs) + f"\n\nHTTPException: {he.status_code} - {he.detail}"
        send_debug_email_sync(current_user.fld_email, "Avatar Upload - HTTP Error Details", email_body)
        raise he
    except Exception as e:
        tb_str = traceback.format_exc()
        log_print(f"Unexpected Error: {str(e)}\n{tb_str}")
        email_body = "\n".join(debug_logs)
        send_debug_email_sync(current_user.fld_email, "Avatar Upload - System Error Details", email_body)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
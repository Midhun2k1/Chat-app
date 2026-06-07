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


MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB
# We allow any content type starting with "image/"
ALLOWED_PREFIX = "image/"

@router.post("/users-avatar", response_model=StandardResponse[dict])
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Validate File Content Type
    if not file.content_type or not file.content_type.startswith(ALLOWED_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only image files are allowed."
        )

    # 2. Validate File Size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    print("file_size",file_size)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large. Maximum size is 30MB."
        )

    # 3. Read image bytes and compress
    try:
        raw_bytes = file.file.read()
        compressed_bytes = compress_image(raw_bytes, file.content_type)
        print("compressed_bytes",compressed_bytes)
    except Exception as e:
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
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not delete old avatar object '{old_avatar}': {str(e)}")

    # 5. Generate unique object name and upload
    object_name = storage_service.generate_object_name("profile-photos", file.filename)
    try:
        storage_service.upload_file(compressed_bytes, object_name, content_type=file.content_type)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to OCI Object Storage: {str(e)}"
        )

    # 6. Save OCI object path in the database
    current_user.fld_avatar_url = object_name
    db.commit()
    db.refresh(current_user)

    # 7. Generate public URL dynamically to return to the client
    avatar_url = storage_service.get_public_avatar_url(object_name)

    return success_response(
        data={"avatar_url": avatar_url},
        message="Profile picture uploaded successfully"
    )
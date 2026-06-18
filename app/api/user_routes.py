from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status
from app.utils.debug_email import send_debug_email_sync
import os
import shutil
import logging
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from app.db.database import get_db
from app.db.models import User, FCMToken
from app.auth.dependencies import get_current_user
from app.schemas.user import (
    UserSearchResponse, UserList, UserSearchRequest,
    FCMTokenRegisterRequest, FCMTokenRegisterResponse,
    FCMTokenDeleteRequest, FCMTokenDeleteResponse
)
from app.schemas.response import StandardResponse
from app.utils.response_utils import success_response
from app.services.object_storage import storage_service
from app.utils.image_utils import compress_image    
from datetime import datetime, timezone

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
    try:
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
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is too large. Maximum size is 30MB."
            )

        # 3. Read image bytes and compress
        try:
            raw_bytes = file.file.read()
            compressed_bytes = compress_image(raw_bytes, file.content_type)
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.delete("/users-avatar", response_model=StandardResponse[dict])
def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete the authenticated user's profile picture.
    Removes the file from object storage (if stored) and clears the avatar URL in the DB.
    """
    old_avatar = current_user.fld_avatar_url
    if not old_avatar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile picture to delete."
        )
    # Delete from storage if it's an object name (not an external URL)
    if not (old_avatar.startswith("http://") or old_avatar.startswith("https://") or old_avatar.startswith("/static/")):
        try:
            storage_service.delete_file(old_avatar)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not delete avatar '{old_avatar}': {str(e)}")
    # Clear avatar URL in DB
    current_user.fld_avatar_url = None
    db.commit()
    db.refresh(current_user)
    return success_response(data={}, message="Profile picture deleted successfully")


@router.post("/fcm-token", response_model=StandardResponse[FCMTokenRegisterResponse])
def register_fcm_token(
    request: FCMTokenRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print("fcm-token entry")
    token = request.token.strip()
    print(token, "token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token cannot be empty"
        )
    
    # Check if this token already exists in the database
    existing_token = db.query(FCMToken).filter(FCMToken.fld_token == token).first()
    if existing_token:
        # Update user association and time
        existing_token.fld_user_id = current_user.fld_user_id
        existing_token.fld_updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing_token)
        token_data = existing_token
    else:
        new_token = FCMToken(
            fld_user_id=current_user.fld_user_id,
            fld_token=token
        )
        db.add(new_token)
        db.commit()
        db.refresh(new_token)
        token_data = new_token
        
    response_data = {
        "fld_fcm_token_id": token_data.fld_fcm_token_id,
        "fld_user_id": token_data.fld_user_id,
        "fld_token": token_data.fld_token
    }
    return success_response(data=response_data, message="FCM Token registered successfully")


@router.delete("/fcm-token", response_model=StandardResponse[FCMTokenDeleteResponse])
def delete_fcm_token(
    request: FCMTokenDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    token = request.token.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token cannot be empty"
        )
        
    # Delete token if it belongs to current_user
    db.query(FCMToken).filter(
        FCMToken.fld_token == token,
        FCMToken.fld_user_id == current_user.fld_user_id
    ).delete()
    db.commit()
    
    return success_response(data={"message": "Token deleted successfully"}, message="FCM Token deleted successfully")
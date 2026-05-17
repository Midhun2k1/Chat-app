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
            "avatar_url": user.fld_avatar_url
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
            "avatar_url": user.fld_avatar_url
        }
        for user in users
    ]
    return success_response(data={"users": users_list}, message="Users fetched successfully")


MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB
ALLOWED_EXTENSIONS = {"image/jpeg", "image/png", "image/webp"}

@router.post("/users-avatar", response_model=StandardResponse[dict])
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Validate File Content Type
    if file.content_type not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed."
        )

    # 2. Validate File Size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large. Maximum size is 4MB."
        )

    # 3. Create unique filename
    file_extension = file.filename.split(".")[-1]
    filename = f"avatar_user_{current_user.fld_user_id}.{file_extension}"
    
    # Define upload path
    upload_folder = "static/uploads/avatars"
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)

    # 4. Save file to disk
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {str(e)}"
        )

    # 5. Save the relative path in the database
    avatar_url = f"/static/uploads/avatars/{filename}"
    current_user.fld_avatar_url = avatar_url
    db.commit()
    db.refresh(current_user)

    return success_response(
        data={"avatar_url": avatar_url},
        message="Profile picture uploaded successfully"
    )
from fastapi import APIRouter, Depends, Query
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
            "phone": user.fld_phone
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
            "phone": user.fld_phone
        }
        for user in users
    ]
    return success_response(data={"users": users_list}, message="Users fetched successfully")
from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserRegister(BaseModel):
    #Basic Info
    firstname: str
    lastname: str
    username: str
    #Contact Info
    email: EmailStr
    #Security Info
    password: str


class UserLogin(BaseModel):
    identifier: str
    password: str

class EmailVerification(BaseModel):
    email: EmailStr
    code: str

class ResendOTP(BaseModel):
    email: EmailStr

class UserSearchResponse(BaseModel):
    user_id: int
    username: str
    firstname: str
    lastname: str
    email: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True

class UserList(BaseModel):
    users: List[UserSearchResponse]

class AuthResponseData(BaseModel):
    access_token: str
    refresh_token: str
    user_id: int
    is_verified: bool

class UserMeResponse(BaseModel):
    user_id: int
    username: str
    email: str
    is_verified: bool
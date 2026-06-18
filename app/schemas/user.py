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
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class UserList(BaseModel):
    users: List[UserSearchResponse]

class UserSearchRequest(BaseModel):
    query: str

class AuthResponseData(BaseModel):
    access_token: str
    refresh_token: str
    user_id: int
    is_verified: bool
    username: str
    email: str
    avatar_url: Optional[str] = None
    full_name: str

class UserMeResponse(BaseModel):
    user_id: int
    username: str
    email: str
    is_verified: bool
    avatar_url: Optional[str] = None
    full_name: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str

class VerifyOTPResponse(BaseModel):
    user_id: int

class ResetPasswordByIdRequest(BaseModel):
    user_id: int
    new_password: str

class FCMTokenRegisterRequest(BaseModel):
    token: str

class FCMTokenRegisterResponse(BaseModel):
    fld_fcm_token_id: int
    fld_user_id: int
    fld_token: str

    class Config:
        from_attributes = True

class FCMTokenDeleteRequest(BaseModel):
    token: str

class FCMTokenDeleteResponse(BaseModel):
    message: str
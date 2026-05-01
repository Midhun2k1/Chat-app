from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRegister(BaseModel):
    #Basic Info
    firstname: str
    lastname: str
    username: str
    #Contact Info
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    #Security Info
    password: str


class UserLogin(BaseModel):
    username: str
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
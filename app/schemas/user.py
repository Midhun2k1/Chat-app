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
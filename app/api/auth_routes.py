from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.schemas.user import UserRegister, UserLogin
from app.auth.auth import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user


router = APIRouter()


@router.post("/register")
def user_register(user: UserRegister, db: Session = Depends(get_db)):
    try:
        if not user.email and not user.phone:
            raise HTTPException(status_code=400, detail="UserRegister")
        
        existing_user = db.query(User).filter(User.fld_username == user.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exist")
        
        if user.email:
            if db.query(User).filter(User.fld_email == user.email).first():
                raise HTTPException(status_code=400, detail="Email is already registered")
            
        if user.phone:
            if db.query(User).filter(User.fld_phone == user.phone).first():
                raise HTTPException(status_code=400, detail="Phone number is already registered")
            
        hashed_password = hash_password(user.password)
        new_user = User(
            fld_firstname = user.firstname,
            fld_lastname = user.lastname,
            fld_username = user.username,
            fld_email = user.email,
            fld_phone = user.phone,
            fld_hashed_password = hashed_password
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {"message": "user registered successfully"}
    except Exception as e:
        return str(e)


@router.post("/login")
def user_login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.fld_username == user.username).first()
        if not db_user:
            raise HTTPException(status_code=400, detail="Username not found!")
        
        if not verify_password(user.password, db_user.fld_hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password!")
        
        access_token = create_access_token(
            data={"user_id": db_user.fld_user_id}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        return str(e)
    

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "user_id": current_user.fld_user_id,
        "username": current_user.fld_username,
        "email": current_user.fld_email
    }
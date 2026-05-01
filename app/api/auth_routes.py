from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.schemas.user import UserRegister, UserLogin, EmailVerification, ResendOTP, AuthResponseData, UserMeResponse
from app.schemas.token import Token, RefreshTokenRequest
from app.schemas.response import StandardResponse, ErrorResponse
from app.auth.auth import hash_password, verify_password, create_access_token, create_refresh_token, SECRET_KEY, ALGORITHM
from app.auth.dependencies import get_current_user
from app.utils.otp_utils import generate_otp
from app.services.email_service import send_verification_email
from jose import JWTError, jwt
from sqlalchemy import or_


router = APIRouter()

common_responses = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@router.post("/register", response_model=StandardResponse[AuthResponseData], responses=common_responses)
def user_register(user: UserRegister, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(User).filter(User.fld_username == user.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exist")

        if db.query(User).filter(User.fld_email == user.email).first():
            raise HTTPException(status_code=400, detail="Email is already registered")
            
        hashed_password = hash_password(user.password)
        new_user = User(
            fld_firstname = user.firstname,
            fld_lastname = user.lastname,
            fld_username = user.username,
            fld_email = user.email,
            fld_hashed_password = hashed_password
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        access_token = create_access_token(
            data={"user_id": new_user.fld_user_id}
        )
        refresh_token = create_refresh_token(
            data={"user_id": new_user.fld_user_id}
        )

        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": new_user.fld_user_id,
            "is_verified": new_user.fld_is_verified
        }

        return {
            "success": True,
            "status": 200,
            "message": "User registered and logged in successfully",
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=StandardResponse[AuthResponseData], responses=common_responses)
def user_login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(
            or_(
                User.fld_username == user.identifier,
                User.fld_email == user.identifier
            )
        ).first()
        if not db_user:
            raise HTTPException(status_code=400, detail="User not found!")
        
        if not verify_password(user.password, db_user.fld_hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password!")
        
        access_token = create_access_token(
            data={"user_id": db_user.fld_user_id}
        )
        refresh_token = create_refresh_token(
            data={"user_id": db_user.fld_user_id}
        )

        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": db_user.fld_user_id,
            "is_verified": db_user.fld_is_verified
        }
        return {
            "success": True,
            "status": 200,
            "message": "Login successful",
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-verification", response_model=StandardResponse[None], responses=common_responses)
async def send_verification(
    request: ResendOTP, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # If the email is different, update it
    if request.email != current_user.fld_email:
        # Check if the new email is already registered
        existing_user = db.query(User).filter(User.fld_email == request.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email is already registered by another user")
        
        current_user.fld_email = request.email
        current_user.fld_is_verified = False
    
    elif current_user.fld_is_verified:
        return {
            "success": True,
            "status": 200,
            "message": "Email is already verified"
        }
    
    otp = generate_otp()
    current_user.fld_verification_code = otp
    db.commit()
    
    await send_verification_email(current_user.fld_email, otp)
    
    return {
        "success": True,
        "status": 200,
        "message": f"Verification code sent to {current_user.fld_email}"
    }


@router.post("/verify-email", response_model=StandardResponse[None], responses=common_responses)
def verify_email(request: EmailVerification, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.fld_email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.fld_is_verified:
        return {
            "success": True,
            "status": 200,
            "message": "Email is already verified"
        }
    
    if user.fld_verification_code != request.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    user.fld_is_verified = True
    user.fld_verification_code = None  # Clear the code after verification
    db.commit()
    
    return {
        "success": True,
        "status": 200,
        "message": "Email verified successfully"
    }


@router.post("/refresh", response_model=StandardResponse[Token], responses=common_responses)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        token_type: str = payload.get("token_type")

        if user_id is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        db_user = db.query(User).filter(User.fld_user_id == user_id).first()
        if not db_user:
            raise HTTPException(status_code=401, detail="User not found")

        new_access_token = create_access_token(data={"user_id": db_user.fld_user_id})
        new_refresh_token = create_refresh_token(data={"user_id": db_user.fld_user_id})

        data = {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        return {
            "success": True,
            "status": 200,
            "message": "Token refreshed successfully",
            "data": data
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/me", response_model=StandardResponse[UserMeResponse], responses=common_responses)
def get_me(current_user: User = Depends(get_current_user)):
    data = {
        "user_id": current_user.fld_user_id,
        "username": current_user.fld_username,
        "email": current_user.fld_email,
        "is_verified": current_user.fld_is_verified
    }
    return {
        "success": True,
        "status": 200,
        "message": "User details fetched successfully",
        "data": data
    }

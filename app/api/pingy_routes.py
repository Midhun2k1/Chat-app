from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.response import ErrorResponse, StandardResponse
from app.auth.dependencies import get_current_user
from app.schemas.pingy import PingyDetails
from sqlalchemy.orm import Session
from app.db.database import get_db
from sqlalchemy import func, distinct
from app.db.models import User, ConversationParticipant
from app.services.object_storage import storage_service

router = APIRouter()

common_responses = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}

@router.get("/pingy-details", response_model=StandardResponse[PingyDetails], responses=common_responses)
def get_pingy_details(current_user = Depends(get_current_user), db: Session = Depends(get_db)):

    pingy_user = db.query(User).filter(User.fld_user_id == 999).first()
    if not pingy_user:
        raise HTTPException(status_code=404, detail="Pingy user not found")
    # Fetch conversation ID where both the pingy user and the current user are participants
    subq = (
        db.query(ConversationParticipant.fld_conversation_id)
        .filter(ConversationParticipant.fld_user_id.in_([pingy_user.fld_user_id, current_user.fld_user_id]))
        .group_by(ConversationParticipant.fld_conversation_id)
        .having(func.count(distinct(ConversationParticipant.fld_user_id)) == 2)
        .subquery()
    )
    
    conv_entry = db.query(subq.c.fld_conversation_id).first()
    conversation_id = conv_entry[0] if conv_entry else None
    
    data = PingyDetails(
        username=pingy_user.fld_username,
        chatId=str(conversation_id) if conversation_id else "",
        avatarUrl=storage_service.get_public_avatar_url(pingy_user.fld_avatar_url),
        pingyUserId=str(pingy_user.fld_user_id),
        isEnabled=pingy_user.fld_is_bot,
    )

    return {
        "success": True,
        "status": 200,
        "message": "Pingy details retrieved",
        "data": data
    }

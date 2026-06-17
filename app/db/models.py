from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, Text
from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
from .database import Base

class User(Base):
    __tablename__ = "tbl_users"

    fld_user_id = Column(Integer, primary_key=True, index=True)

    fld_firstname = Column(String(50), nullable=False)
    fld_lastname = Column(String(50), nullable=False)
    fld_username = Column(String(50), unique=True, index=True, nullable=False)

    fld_email = Column(String(100), unique=True, index=True, nullable=True)
    fld_phone = Column(String(15), unique=True, index=True, nullable=True)

    fld_hashed_password = Column(String(255), nullable=False)

    fld_is_active = Column(Boolean, default=True)
    fld_is_verified = Column(Boolean, default=False)
    fld_verification_code = Column(String(10), nullable=True)
    fld_reset_code = Column(String(10), nullable=True)
    fld_reset_code_expiry = Column(DateTime(timezone=True), nullable=True)
    fld_avatar_url = Column(String(255), nullable=True, default=None)
    fld_is_bot = Column(Boolean, default=False, nullable=False, server_default="false")

    fld_created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    fld_updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))


class Conversation(Base):
    __tablename__ = "tbl_converssation"

    fld_conversation_Id = Column(Integer, primary_key=True, index=True)

    fld_created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ConversationParticipant(Base):
    __tablename__ = "tbl_conversation_participants"

    fld_conversation_participants_Id = Column(Integer, primary_key=True, index=True)

    fld_conversation_id = Column(Integer, ForeignKey("tbl_converssation.fld_conversation_Id"))
    fld_user_id = Column(Integer, ForeignKey("tbl_users.fld_user_id"))


class Message(Base):
    __tablename__ = "tbl_messages"

    fld_message_id = Column(Integer, primary_key=True, index=True)

    fld_sender_id = Column(Integer, ForeignKey("tbl_users.fld_user_id"), nullable=False)
    #fld_receiver_id = Column(Integer, ForeignKey("tbl_users.fld_user_id"), nullable=False)
    fld_conversation_id = Column(Integer, ForeignKey("tbl_converssation.fld_conversation_Id"))
    fld_client_message_id =  Column(String(100), nullable=False)

    fld_message = Column(String, nullable=False)
    fld_is_read = Column(Boolean, default=False)  

    fld_is_deleted_for_everyone = Column(Boolean, default=False)
    fld_is_edited = Column(Boolean, default=False, server_default="false", nullable=False)
    fld_created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    fld_deleted_for_everyone_at = Column(DateTime(timezone=True), nullable=True)
    fld_parent_message_id = Column(String(100), nullable=True)
    fld_embedding = Column(Vector(384), nullable=True)


class MessageDelete(Base):
    __tablename__ = "tbl_message_deletes"

    fld_message_delete_id = Column(Integer, primary_key=True)

    fld_message_id = Column(Integer, ForeignKey("tbl_messages.fld_message_id"))
    fld_user_id = Column(Integer, ForeignKey("tbl_users.fld_user_id"))

    fld_deleted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
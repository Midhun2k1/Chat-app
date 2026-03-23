from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, Text
from datetime import datetime
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

    fld_created_at = Column(DateTime, default=datetime.utcnow)
    fld_updated_at = Column(DateTime, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "tbl_converssation"

    fld_conversation_Id = Column(Integer, primary_key=True, index=True)

    fld_created_at = Column(DateTime, default=datetime.utcnow)


class ConversationParticipant(Base):
    __tablename__ = "tbl_conversation_participants"

    fld_conversation_participants_Id = Column(Integer, primary_key=True, index=True)

    fld_conversation_id = Column(Integer, ForeignKey("tbl_converssation.fld_conversation_Id"))
    fld_user_id = Column(Integer, ForeignKey("tbl_users.fld_user_id"))


""" class Message(Base):
    __tablename__ = "tbl_messages"

    fld_message_Id = Column(Integer, primary_key=True, index=True)

    fld_conversation_id = Column(Integer, ForeignKey("tbl_converssation.fld_conversation_Id"))
    fld_sender_id = Column(Integer, ForeignKey("tbl_users.fld_user_id"))

    fld_message = Column(Text, nullable=False)
    fld_created_at = Column(DateTime, default=datetime.utcnow) """


class Message(Base):
    __tablename__ = "tbl_messages"

    fld_message_id = Column(Integer, primary_key=True, index=True)

    fld_sender_id = Column(Integer, ForeignKey("tbl_users.fld_user_id"), nullable=False)
    fld_receiver_id = Column(Integer, ForeignKey("tbl_users.fld_user_id"), nullable=False)
    fld_conversation_id = Column(Integer, ForeignKey("tbl_converssation.fld_conversation_Id"))

    fld_message = Column(String, nullable=False)
    fld_created_at = Column(DateTime, default=datetime.utcnow)
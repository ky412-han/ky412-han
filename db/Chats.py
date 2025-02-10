from sqlalchemy.orm import Session
from .models import Chat
import logging

logger = logging.getLogger(__name__)

# 경로 생성
from sqlalchemy.exc import SQLAlchemyError

def create_chat(db: Session, user_id: int, message: str) -> Chat:
    try:
        """새로운 채팅 메시지를 생성합니다."""
        new_chat = Chat(user_id=user_id, message=message)
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
        logger.info(f"Chat created: {new_chat.id}, User ID: {user_id}")
        return new_chat
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error creating chat for user {user_id}: {str(e)}")
        raise e

# 특정 사용자의 모든 채팅 가져오기
def get_user_chats(db: Session, user_id: int, limit: int = 20, offset: int = 0) -> list[Chat]:
    """
    특정 사용자의 모든 채팅 기록을 가져옵니다.
    limit와 offset을 사용해 페이징 처리 가능.
    """
    try:
        chats = db.query(Chat).filter(Chat.user_id == user_id).offset(offset).limit(limit).all()
        logger.info(f"{len(chats)} chats retrieved for user {user_id}")
        return chats
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving chats for user {user_id}: {str(e)}")
        raise e

# 특정 채팅 삭제
def delete_chat(db: Session, chat_id: int):
    """특정 채팅 메시지를 삭제합니다."""
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            raise ValueError(f"Chat with ID {chat_id} not found.")
        db.delete(chat)
        db.commit()
        logger.info(f"Chat deleted: {chat_id}")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error deleting chat {chat_id}: {str(e)}")
        raise e

# 특정 사용자의 모든 채팅 삭제
def delete_user_chats(db: Session, user_id: int):
    """특정 사용자의 모든 채팅 기록을 삭제합니다."""
    try:
        chats_deleted = db.query(Chat).filter(Chat.user_id == user_id).delete()
        db.commit()
        logger.info(f"All chats deleted for user {user_id}")
        return chats_deleted > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error deleting chats for user {user_id}: {str(e)}")
        raise e
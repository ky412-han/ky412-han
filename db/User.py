from sqlalchemy.orm import Session
from .models import User
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

# Create or Get User
def get_or_create_user(db: Session, email: str, name: str):
    try:
        # 기존 사용자 확인
        user = db.query(User).filter(User.email == email).first()
        if user:
            return user
        
        # 사용자 생성
        new_user = User(email=email, name=name)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"New user created: {new_user.email}")
        return new_user
    except SQLAlchemyError as e:
        db.rollback()  # 데이터베이스 트랜잭션 롤백
        logger.error(f"Error in get_or_create_user: {str(e)}")
        raise e


def delete_account(db: Session, user_id: int):
    # 사용자 조회
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.info(f"User with ID {user_id} not found.")
            return False
        
        db.delete(user)
        db.commit()
        logger.info(f"User with ID {user_id} and associated data deleted.")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error in delete_account: {str(e)}")
        raise e
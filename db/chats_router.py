from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .Chats import create_chat, get_user_chats, delete_chat
from .db import get_db


router = APIRouter()

# 데이터 모델 정의
class ChatCreate(BaseModel):
    message: str

# 채팅 추가
@router.post("/chats/")
def add_route(user_id: int, chat: ChatCreate, db: Session = Depends(get_db)):
    """
    사용자에게 새로운 채팅 메시지를 추가합니다.
    """
    try:
        new_chat = create_chat(db, user_id=user_id, message=chat.message)
        return {"id": new_chat.id, "message": "Chat added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 특정 사용자의 채팅 목록 가져오기
@router.get("/chats/{user_id}")
def list_chats(user_id: int, limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    """
    특정 사용자의 모든 채팅을 가져옵니다.
    """
    chats = get_user_chats(db, user_id=user_id, limit=limit, offset=offset)
    if not chats:
        raise HTTPException(status_code=404, detail="No chats found for the user")
    return chats

# 특정 채팅 삭제
@router.delete("/chats/{chat_id}")
def remove_chat(chat_id: int, db: Session = Depends(get_db)):
    """
    특정 채팅 메시지를 삭제합니다.
    """
    try:
        if not delete_chat(db, chat_id=chat_id):
            raise HTTPException(status_code=404, detail="Chat not found")
        return {"message": "Chat deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
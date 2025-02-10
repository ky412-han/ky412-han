from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .User import get_or_create_user, delete_account
from .db import get_db


router = APIRouter()

@router.post("/users/")
def create_user(email: str, name: str, db: Session = Depends(get_db)):
    return get_or_create_user(db, email, name)

@router.delete("/users/{user_id}")
def remove_user(user_id: int, db: Session = Depends(get_db)):
    if not delete_account(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

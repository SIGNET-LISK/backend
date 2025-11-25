from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from indexer.db import get_db
from models.content import Content

router = APIRouter()

@router.get("/contents")
def get_contents(db: Session = Depends(get_db)):
    contents = db.query(Content).order_by(Content.created_at.desc()).limit(100).all()
    return contents

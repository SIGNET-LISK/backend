import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import register, verify, contents
from indexer.db import engine
from models.content import Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SIGNET Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(register.router, prefix="/api", tags=["Register"])
app.include_router(verify.router, prefix="/api", tags=["Verify"])
app.include_router(contents.router, prefix="/api", tags=["Contents"])

@app.get("/")
def root():
    return {"message": "SIGNET Backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import register, verify, contents, signature, admin
from indexer.db import engine
from models.content import Base
from dotenv import load_dotenv

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SIGNET Backend API")

# CORS Configuration
# Allow origins from environment variable or default to all origins
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# Parse comma-separated origins if provided
if CORS_ORIGINS != "*":
    allowed_origins = [origin.strip() for origin in CORS_ORIGINS.split(",")]
else:
    allowed_origins = ["*"]

# If using wildcard, disable credentials (browser security requirement)
# If using specific origins, we can enable credentials
use_credentials = CORS_ORIGINS != "*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=use_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(register.router, prefix="/api", tags=["Register"])
app.include_router(verify.router, prefix="/api", tags=["Verify"])
app.include_router(contents.router, prefix="/api", tags=["Contents"])
app.include_router(signature.router, prefix="/api", tags=["Signature"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])

@app.get("/")
def root():
    return {"message": "SIGNET Backend is running with gasless transaction support"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
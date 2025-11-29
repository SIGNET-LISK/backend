import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SIGNET Backend API")

# CORS Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
if CORS_ORIGINS != "*":
    allowed_origins = [origin.strip() for origin in CORS_ORIGINS.split(",")]
else:
    allowed_origins = ["*"]

use_credentials = CORS_ORIGINS != "*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=use_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
try:
    from indexer.db import engine
    from models.content import Base
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize database: {e}")
    raise

# Include routers
try:
    from api import register, verify, contents, signature, admin
    app.include_router(register.router, prefix="/api", tags=["Register"])
    app.include_router(verify.router, prefix="/api", tags=["Verify"])
    app.include_router(contents.router, prefix="/api", tags=["Contents"])
    app.include_router(signature.router, prefix="/api", tags=["Signature"])
    app.include_router(admin.router, prefix="/api", tags=["Admin"])
    logger.info("✅ All routers loaded")
except Exception as e:
    logger.error(f"❌ Failed to load routers: {e}")
    raise

@app.get("/")
def root():
    return {"message": "SIGNET Backend is running with gasless transaction support"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
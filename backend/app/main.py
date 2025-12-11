"""
Main FastAPI application entry point
"""
import warnings

# Suppress Pydantic V1 compatibility warning with Python 3.14
# This warning is harmless - Pydantic V2's compatibility layer works fine
# The warning comes from deepgram's internal use of Pydantic V1
warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater",
    category=UserWarning
)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
import logging
import time
import json

from app.api import transcription, ai_processing, email, teams, export, auth, todos, search
from app.database import init_db

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests"""
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request (log path and method, body will be logged by endpoint handlers)
        logger.info(f"[Request] {request.method} {request.url.path} - Query: {dict(request.query_params)}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"[Response] {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    await init_db()
    yield
    # Shutdown (if needed)


app = FastAPI(
    title="Meeting Assistant",
    description="Real-time transcription, MOM generation, and Email/Teams cognitive assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Request logging middleware (must be before CORS)
app.add_middleware(RequestLoggingMiddleware)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transcription.router, prefix="/api/transcribe", tags=["Transcription"])
app.include_router(ai_processing.router, prefix="/api/ai", tags=["AI Processing"])
app.include_router(email.router, prefix="/api/email", tags=["Email"])
app.include_router(teams.router, prefix="/api/teams", tags=["Teams"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(todos.router, prefix="/api/todos", tags=["Todos"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Meeting Assistant API"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.error(f"[Validation Error] {request.method} {request.url.path}: {exc.errors()}")
    # Return 400 for better compatibility (422 is more correct but 400 is more common)
    return JSONResponse(
        status_code=400,
        content={
            "detail": exc.errors(),
            "message": "Request validation failed. Please check your request data.",
            "errors": [f"{err.get('loc', [])}: {err.get('msg', '')}" for err in exc.errors()]
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
            "message": "An unexpected error occurred. Please check the server logs."
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



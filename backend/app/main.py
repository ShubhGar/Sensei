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
import time
import json
import uuid

from app.api import transcription, ai_processing, email, teams, export, auth, todos, search, ai_enhanced
from app.database import init_db
from app.utils.logger import setup_logging, get_logger

load_dotenv()

# Configure centralized logging
setup_logging(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    include_location=True
)
logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming requests with correlation IDs"""
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID for request tracing
        correlation_id = str(uuid.uuid4())[:8]
        request.state.correlation_id = correlation_id
        
        start_time = time.time()
        
        # Log request with correlation ID
        query_params = dict(request.query_params) if request.query_params else {}
        logger.info(
            f"Request started | Method: {request.method} | Path: {request.url.path} | "
            f"Query: {query_params} | CorrelationID: {correlation_id}"
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"Request completed | Method: {request.method} | Path: {request.url.path} | "
                f"Status: {response.status_code} | Time: {process_time:.3f}s | CorrelationID: {correlation_id}"
            )
            
            # Add correlation ID to response headers for client tracing
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed | Method: {request.method} | Path: {request.url.path} | "
                f"Error: {type(e).__name__}: {str(e)} | Time: {process_time:.3f}s | "
                f"CorrelationID: {correlation_id}",
                exc_info=True
            )
            raise


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
app.include_router(ai_enhanced.router, prefix="/api/ai", tags=["AI Enhanced"])
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
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    logger.error(
        f"Validation error | Method: {request.method} | Path: {request.url.path} | "
        f"Errors: {exc.errors()} | CorrelationID: {correlation_id}"
    )
    # Return 400 for better compatibility (422 is more correct but 400 is more common)
    response = JSONResponse(
        status_code=400,
        content={
            "detail": exc.errors(),
            "message": "Request validation failed. Please check your request data.",
            "errors": [f"{err.get('loc', [])}: {err.get('msg', '')}" for err in exc.errors()],
            "correlation_id": correlation_id
        }
    )
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    logger.error(
        f"Unhandled exception | Path: {request.url.path} | "
        f"Type: {type(exc).__name__} | Error: {str(exc)} | CorrelationID: {correlation_id}",
        exc_info=True
    )
    response = JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
            "message": "An unexpected error occurred. Please check the server logs.",
            "correlation_id": correlation_id
        }
    )
    response.headers["X-Correlation-ID"] = correlation_id
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



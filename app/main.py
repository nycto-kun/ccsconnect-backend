from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Existing routers
from app.routes import auth, jobs, announcements, registrar
from app.routes import resources, offers, chat, ai, students
from app.routes import applications, attendance, reports, admin
from app.routes import bookmarks, assignments
from app.routes import notices

app = FastAPI(title="CCSConnect API", version="1.0.0")

# Get allowed origins from environment variable (comma-separated)
# Example: ALLOWED_ORIGINS=http://localhost:5173,https://ccsconnect-frontend.vercel.app,https://ccsconnect-frontend-r4uluj9wj-nycto-kuns-projects.vercel.app
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()]

# Fallback for development
if not ALLOWED_ORIGINS and os.getenv("ENVIRONMENT") != "production":
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]

# In production, if no origins are specified, raise an error
if os.getenv("ENVIRONMENT") == "production" and not ALLOWED_ORIGINS:
    raise ValueError("ALLOWED_ORIGINS environment variable must be set in production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Explicit list of allowed origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Content-Length", "Content-Type"],
    max_age=86400,  # 24 hours cache for preflight requests
)

# Include routers
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(notices.router)
app.include_router(announcements.router)
app.include_router(registrar.router)
app.include_router(resources.router)
app.include_router(offers.router)
app.include_router(chat.router)
app.include_router(ai.router)
app.include_router(students.router)
app.include_router(applications.router)
app.include_router(attendance.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(bookmarks.router)
app.include_router(assignments.router)

@app.get("/")
async def root():
    return {
        "message": "CCSConnect API is running",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.options("/{rest_of_path:path}")
async def preflight_options(rest_of_path: str):
    """Explicit OPTIONS handler for CORS preflight"""
    return {"message": "OK"}
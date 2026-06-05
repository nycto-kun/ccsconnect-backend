from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import all routers - NO 'app.' prefix because we're INSIDE the app folder
from routes import auth
from routes import jobs
from routes import announcements
from routes import registrar
from routes import resources
from routes import offers
from routes import chat
from routes import ai
from routes import students
from routes import applications
from routes import attendance
from routes import reports
from routes import admin
from routes import notices
from routes import bookmarks
from routes import assignments

app = FastAPI(title="CCSConnect API", version="1.0.0")

# CORS Configuration
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "")
if ALLOWED_ORIGINS_STR:
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")]
else:
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "https://ccsconnect-frontend.vercel.app",
        "https://*.vercel.app",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# Include all routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(applications.router, prefix="/applications", tags=["Applications"])
app.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(notices.router, prefix="/notices", tags=["Notices"])
app.include_router(bookmarks.router, prefix="/bookmarks", tags=["Bookmarks"])
app.include_router(assignments.router, prefix="/assignments", tags=["Assignments"])
app.include_router(announcements.router, prefix="/announcements", tags=["Announcements"])
app.include_router(registrar.router, prefix="/registrar", tags=["Registrar"])
app.include_router(resources.router, prefix="/resources", tags=["Resources"])
app.include_router(offers.router, prefix="/offers", tags=["Offers"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(ai.router, prefix="/ai", tags=["AI"])
app.include_router(students.router, prefix="/students", tags=["Students"])

@app.get("/")
async def root():
    return {
        "message": "CCSConnect API is running",
        "docs": "/docs",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/routes")
async def list_routes():
    """Debug endpoint to see all registered routes"""
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "methods": list(route.methods) if hasattr(route, "methods") else [],
        })
    return {"total_routes": len(routes), "routes": routes}
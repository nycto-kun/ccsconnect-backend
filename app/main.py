from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

from app.routes import auth, jobs, applications, attendance, reports, admin
from app.routes import notices, bookmarks, assignments, ai, chat, offers
from app.routes import resources, students, registrar, announcements, companies

app = FastAPI(title="CCSConnect API", version="1.0.0")

# CORS Configuration
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "https://ccsconnect-frontend.vercel.app",
    "https://*.vercel.app",
    "https://ccsconnect-backend.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# OPTIONS handler for all routes
@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    return {"message": "OK"}

# Include routers - WITHOUT trailing slash to match frontend calls
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(applications.router, prefix="/applications", tags=["Applications"])
app.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(notices.router, prefix="/notices", tags=["Notices"])
app.include_router(bookmarks.router, prefix="/bookmarks", tags=["Bookmarks"])
app.include_router(assignments.router, prefix="/assignments", tags=["Assignments"])
app.include_router(ai.router, prefix="/ai", tags=["AI"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(offers.router, prefix="/offers", tags=["Offers"])
app.include_router(resources.router, prefix="/resources", tags=["Resources"])
app.include_router(students.router, prefix="/students", tags=["Students"])
app.include_router(registrar.router, prefix="/registrar", tags=["Registrar"])
app.include_router(announcements.router, prefix="/announcements", tags=["Announcements"])
app.include_router(companies.router, prefix="/companies", tags=["Companies"])

@app.get("/")
async def root():
    return {"message": "CCSConnect API running", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/routes")
async def list_routes():
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "methods": list(route.methods) if hasattr(route, "methods") else [],
        })
    return {"total": len(routes), "routes": routes}
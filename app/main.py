from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request
import os
from dotenv import load_dotenv

load_dotenv()

from app.routes import auth, jobs, applications, attendance, reports, admin
from app.routes import notices, bookmarks, assignments, ai, chat, offers
from app.routes import resources, students, registrar, announcements, companies
from app.routes import upload

app = FastAPI(title="CCSConnect API", version="1.0.0")

# CORS Configuration - FIXED
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "https://ccsconnect-frontend.vercel.app",
        "https://ccsconnect.nport.link",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# OPTIONS handler for preflight requests
@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    response = JSONResponse(content={"message": "OK"})
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin", "")
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# Include routers
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
app.include_router(upload.router, prefix="/upload", tags=["Upload"])

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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers (must come AFTER app is created? Actually import can be here,
# but they are just modules. The important part is to include them after app exists.
# However, having them at the top is fine, as long as you don't CALL app.include_router before app exists.
# The error was calling app.include_router before the line 'app = FastAPI()'.

app = FastAPI(
    title="CCSConnect API",
    description="Backend API for the CCSConnect Internship and Job Portal",
    version="1.0.0"
)

# CORS configuration – allow your frontend domains
origins = [
    "http://localhost:3000",
    "https://ccsconnect-frontend.vercel.app",  # Replace with your actual Vercel URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Now it's safe to include routers ---
from app.routes import auth, jobs, notices, announcements, registrar

app.include_router(auth.router)                 # /auth/*
app.include_router(jobs.router)                 # /jobs/*
app.include_router(notices.router)               # /notices/*
app.include_router(announcements.router)         # /announcements/*
app.include_router(registrar.router)             # /api/registrar/*

@app.get("/")
async def root():
    return {
        "message": "CCSConnect API is running",
        "docs": "/docs",
        "version": "1.0.0"
    }
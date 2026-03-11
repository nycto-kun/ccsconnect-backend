from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.routes import auth, jobs, notices, announcements

app = FastAPI(
    title="CCSConnect API",
    description="Backend API for the CCSConnect Internship and Job Portal",
    version="1.0.0"
)

# CORS configuration – allow your frontend domains
# Replace the placeholder with your actual Vercel frontend URL
origins = [
    "http://localhost:3000",                     # for local development
    "https://ccsconnect-frontend.vercel.app",    # <-- REPLACE WITH YOUR ACTUAL URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)                 # /auth/*
app.include_router(jobs.router)                 # /jobs/*
app.include_router(notices.router)               # /notices/*
app.include_router(announcements.router)         # /announcements/*

@app.get("/")
async def root():
    return {
        "message": "CCSConnect API is running",
        "docs": "/docs",
        "version": "1.0.0"
    }
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Existing routers
from app.routes import auth, jobs, announcements, registrar
from app.routes import resources, offers, chat, ai, students
# New routers
from app.routes import applications, attendance, reports, admin
from app.routes import bookmarks, assignments
# Replace old notices router with the full CRUD version
from app.routes import notices  # this should be the new CRUD version

app = FastAPI(title="CCSConnect API", version="1.0.0")

origins = [
    "http://localhost:3000",
    "https://ccsconnect-frontend.vercel.app",
    # add other frontend URLs as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)               # /auth
app.include_router(jobs.router)               # /jobs
app.include_router(notices.router)            # /notices (full CRUD)
app.include_router(announcements.router)      # /announcements
app.include_router(registrar.router)          # /api/registrar
app.include_router(resources.router)          # /resources
app.include_router(offers.router)             # /offers
app.include_router(chat.router)               # /chat
app.include_router(ai.router)                 # /ai
app.include_router(students.router)           # /students
app.include_router(applications.router)       # /applications
app.include_router(attendance.router)         # /attendance
app.include_router(reports.router)            # /reports
app.include_router(admin.router)              # /admin
app.include_router(bookmarks.router)    # /bookmarks
app.include_router(assignments.router)  # /assignments

@app.get("/")
async def root():
    return {"message": "CCSConnect API is running", "docs": "/docs", "version": "1.0.0"}
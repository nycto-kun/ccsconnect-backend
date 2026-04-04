from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, jobs, notices, announcements, registrar
from app.routes import resources, offers, chat, ai, students   # new

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

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(notices.router)
app.include_router(announcements.router)
app.include_router(registrar.router)

# New routers
app.include_router(resources.router)
app.include_router(offers.router)
app.include_router(chat.router)
app.include_router(ai.router)
app.include_router(students.router)

@app.get("/")
async def root():
    return {"message": "CCSConnect API is running", "docs": "/docs", "version": "1.0.0"}
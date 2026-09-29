
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import analyze
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="IS Recommendation Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # FIXED: Cannot be True when allow_origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api", tags=["Analysis"])

@app.get("/")
def health_check():
    return {"status": "healthy", "message": "API is running"}

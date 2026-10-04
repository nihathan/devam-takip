import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import engine, Base
from .api import students, attendance, analytics, auth

# Veritabanı tablolarını oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Devam Takip API",
    description="Öğrenci Devamsızlık Analizi, Erken Uyarı ve Veli SMS Bildirim Sistemi",
    version="1.0.0"
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router'ları ekle
app.include_router(auth.router)
app.include_router(students.router)
app.include_router(attendance.router)
app.include_router(analytics.router)

# Frontend arayüzünü sun
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
INDEX_FILE = os.path.join(FRONTEND_DIR, "index.html")

@app.get("/", tags=["Arayüz"])
def serve_ui():
    """
    Ana web dashboard arayüzünü döndürür.
    """
    if os.path.exists(INDEX_FILE):
        return FileResponse(INDEX_FILE)
    return {"message": "Devam Takip API Aktif. Lütfen /docs adresini ziyaret edin."}

@app.get("/health", tags=["Sistem"])
def health_check():
    return {"status": "healthy", "service": "Devam Takip"}

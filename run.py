import sys
import os
import uvicorn

# backend klasörünü modül yoluna ekle
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    print("\n" + "="*60)
    print(" 🚀 DEVAM TAKİP SİSTEMİ BAŞLATILIYOR...")
    print(" 🌐 Web Paneli: http://localhost:8000")
    print(" 📑 Swagger API Dokümantasyonu: http://localhost:8000/docs")
    print("="*60 + "\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

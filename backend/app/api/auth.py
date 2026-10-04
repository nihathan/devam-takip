import secrets
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, UserRole
from ..services.auth_service import authenticate_user, create_user

router = APIRouter(prefix="/api/auth", tags=["Kimlik Doğrulama & Kullanıcı Girişi"])

class LoginRequest(BaseModel):
    username: str
    password: str

class UserProfileResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str
    user: UserProfileResponse

class RegisterUserRequest(BaseModel):
    username: str
    password: str
    full_name: str
    role: UserRole = UserRole.ADMIN

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    İdareci veya öğretmen girişi doğrulaması.
    """
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı!"
        )
    
    # Basit ve güvenli oturum token'ı
    token = f"session_{user.id}_{secrets.token_hex(16)}"

    return LoginResponse(
        success=True,
        message="Giriş başarılı.",
        token=token,
        user=UserProfileResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active
        )
    )

@router.get("/users", response_model=List[UserProfileResponse])
def list_users(db: Session = Depends(get_db)):
    """
    Kayıtlı sistem kullanıcılarını listeler.
    """
    return db.query(User).all()

@router.post("/register", response_model=UserProfileResponse)
def register(payload: RegisterUserRequest, db: Session = Depends(get_db)):
    """
    Yeni bir yönetici veya öğretmen hesabı ekler.
    """
    existing = db.query(User).filter(User.username == payload.username.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten alınmış.")
    
    new_user = create_user(
        db=db,
        username=payload.username,
        password=payload.password,
        full_name=payload.full_name,
        role=payload.role
    )
    return new_user

import hashlib
import secrets
import hmac
from typing import Tuple, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import User, UserRole

SECRET_KEY = "devam-takip-super-secret-key-change-in-production"

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Parolayı PBKDF2-HMAC-SHA256 ve rastgele salt ile güvenli şekilde hashler.
    """
    if not salt:
        salt = secrets.token_hex(16)
    
    pwd_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    hashed = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000)
    return hashed.hex(), salt

def verify_password(password: str, hashed: str, salt: str) -> bool:
    """
    Girilen parolayı kayıtlı hash ile güvenli şekilde (timing-attack korumalı) karşılaştırır.
    """
    calculated_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(calculated_hash, hashed)

def create_user(
    db: Session,
    username: str,
    password: str,
    full_name: str,
    role: UserRole = UserRole.ADMIN
) -> User:
    """
    Yeni kullanıcı hesabı oluşturur.
    """
    hashed, salt = hash_password(password)
    user = User(
        username=username.strip().lower(),
        full_name=full_name.strip(),
        role=role,
        password_hash=hashed,
        salt=salt,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Kullanıcı adı ve parolayı doğrular.
    """
    user = db.query(User).filter(User.username == username.strip().lower(), User.is_active == True).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash, user.salt):
        return None
    return user

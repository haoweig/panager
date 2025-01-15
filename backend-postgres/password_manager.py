from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pyotp
from cryptography.fernet import Fernet
import os
import qrcode
from typing import Optional
import base64
from io import BytesIO
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import text

app = FastAPI()

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Models
class User(BaseModel):
    username: str

class TOTPVerification(BaseModel):
    username: str
    code: str

class PasswordEntry(BaseModel):
    service: str
    service_username: str
    encrypted_password: str

# Database setup
DATABASE_URL = "postgresql://myuser:mypassword@localhost:5432/password_manager"  # Update with your credentials
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class DBPassword(Base):
    __tablename__ = "passwords"

    id = Column(String, primary_key=True)
    app_username = Column(String, nullable=False)
    service = Column(String, nullable=False)
    service_username = Column(String, nullable=False)
    encrypted_password = Column(String, nullable=False)
    last_rotated = Column(DateTime, nullable=False)

class DBUser(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True)
    totp_secret = Column(String, nullable=False)
    registered_at = Column(DateTime, nullable=False)

# Generate and store encryption key in the database
class DBEncryptionKey(Base):
    __tablename__ = "encryption_keys"

    id = Column(String, primary_key=True, default="current")
    key = Column(Text, nullable=False)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database and get encryption key
def get_encryption_key(db: Session) -> bytes:
    key_record = db.query(DBEncryptionKey).filter_by(id="current").first()
    if not key_record:
        new_key = Fernet.generate_key()
        key_record = DBEncryptionKey(id="current", key=new_key.decode())
        db.add(key_record)
        db.commit()
    return key_record.key.encode()

# Create all tables
Base.metadata.create_all(bind=engine)

# Initialize encryption key
with SessionLocal() as db:
    ENCRYPTION_KEY = get_encryption_key(db)

# Updated PasswordManager Class for PostgreSQL
class PasswordManager:
    def __init__(self, encryption_key: bytes):
        self.key = encryption_key
    
    def add_password(self, db: Session, app_username: str, service: str, service_username: str, password: str):
        f = Fernet(self.key)
        encrypted = f.encrypt(password.encode()).decode()
        
        # Create new password entry
        db_password = DBPassword(
            id=f"{app_username}_{service}_{service_username}",
            app_username=app_username,
            service=service,
            service_username=service_username,
            encrypted_password=encrypted,
            last_rotated=datetime.now()
        )
        
        # Check if entry exists and update if it does
        existing = db.query(DBPassword).filter(
            DBPassword.app_username == app_username,
            DBPassword.service == service,
            DBPassword.service_username == service_username
        ).first()
        
        if existing:
            existing.encrypted_password = encrypted
            existing.last_rotated = datetime.now()
        else:
            db.add(db_password)
            
        db.commit()

    def get_password(self, db: Session, app_username: str, service: str) -> list:
        passwords = db.query(DBPassword).filter(
            DBPassword.app_username == app_username,
            DBPassword.service.ilike(f"%{service}%")
        ).all()
        
        f = Fernet(self.key)
        result = []
        
        for password in passwords:
            decrypted_entry = {
                'service': password.service,
                'username': password.service_username,
                'password': f.decrypt(password.encrypted_password.encode()).decode(),
                'last_rotated': password.last_rotated.isoformat()
            }
            result.append(decrypted_entry)
            
        return result

password_manager = PasswordManager(ENCRYPTION_KEY)

# API Routes
@app.post("/register")
async def register_user(user: User, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(DBUser).filter_by(username=user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    totp_secret = pyotp.random_base32()
    totp = pyotp.TOTP(totp_secret)
    
    # Generate QR code
    provisioning_uri = totp.provisioning_uri(user.username, issuer_name="Password Manager")
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img_buffer = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(img_buffer)
    qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Create new user in database
    new_user = DBUser(
        username=user.username,
        totp_secret=totp_secret,
        registered_at=datetime.now()
    )
    db.add(new_user)
    db.commit()
    
    return {
        "message": "User registered successfully",
        "qr_code": qr_base64,
        "secret": totp_secret
    }

@app.post("/verify-totp")
async def verify_totp(verification: TOTPVerification, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter_by(username=verification.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(verification.code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    
    return {"message": "Authentication successful"}

@app.get("/passwords/{app_username}/{service}")
async def get_passwords(app_username: str, service: str, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter_by(username=app_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return password_manager.get_password(db, app_username, service)

@app.post("/passwords/{app_username}")
async def add_password(app_username: str, entry: PasswordEntry, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter_by(username=app_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    password_manager.add_password(
        db=db,
        app_username=app_username,
        service=entry.service,
        service_username=entry.service_username,
        password=entry.encrypted_password
    )
    return {"message": "Password added successfully"}
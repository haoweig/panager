from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pyotp
import pandas as pd
from cryptography.fernet import Fernet
import csv
import os
import qrcode
import json
from typing import Optional
import base64
from io import BytesIO

app = FastAPI()

# CORS middleware setup remains the same
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Updated Data Models
class User(BaseModel):
    username: str

class TOTPVerification(BaseModel):
    username: str
    code: str

class PasswordEntry(BaseModel):
    service: str
    service_username: str  # Changed from username to service_username
    encrypted_password: str

# File paths setup remains the same
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
PASSWORDS_FILE = os.path.join(BASE_DIR, "passwords.csv")
KEY_FILE = os.path.join(BASE_DIR, "encryption_key.key")

# Initialize encryption key (same as before)
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(Fernet.generate_key())

with open(KEY_FILE, "rb") as key_file:
    ENCRYPTION_KEY = key_file.read()

# Initialize users file (same as before)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

def get_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

# Updated PasswordManager Class
class PasswordManager:
    def __init__(self, csv_path: str, encryption_key: bytes):
        self.csv_path = csv_path
        self.key = encryption_key
        self.ensure_csv_exists()
    
    def ensure_csv_exists(self):
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['app_username', 'service', 'service_username', 'encrypted_password', 'last_rotated'])

    def add_password(self, app_username: str, service: str, service_username: str, password: str):
        f = Fernet(self.key)
        # encrypt expects bytes and not strings
        encrypted = f.encrypt(password.encode()).decode()
        df = pd.read_csv(self.csv_path)
        new_row = pd.DataFrame({
            'app_username': [app_username],
            'service': [service],
            'service_username': [service_username],
            'encrypted_password': [encrypted],
            'last_rotated': [pd.Timestamp.now()]
        })
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(self.csv_path, index=False)

    def get_password(self, app_username: str, service: str) -> list:
        df = pd.read_csv(self.csv_path)
        matches = df[(df['app_username'] == app_username) & (df['service'].str.contains(service, case=False))]
        f = Fernet(self.key)
        result = []
        for _, row in matches.iterrows():
            decrypted_entry = {
                'service': row['service'],
                'username': row['service_username'],
                'password': f.decrypt(row['encrypted_password'].encode()).decode(),
                'last_rotated': row['last_rotated']
            }
            result.append(decrypted_entry)
        return result

password_manager = PasswordManager(PASSWORDS_FILE, ENCRYPTION_KEY)

# API Routes (register and verify-totp remain the same)
@app.post("/register")
async def register_user(user: User):
    users = get_users()
    if user.username in users:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    totp_secret = pyotp.random_base32()
    totp = pyotp.TOTP(totp_secret)
    
    provisioning_uri = totp.provisioning_uri(user.username, issuer_name="Password Manager")
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img_buffer = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(img_buffer)
    qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    users[user.username] = {
        "totp_secret": totp_secret,
        "registered_at": pd.Timestamp.now().isoformat()
    }
    save_users(users)
    
    return {
        "message": "User registered successfully",
        "qr_code": qr_base64,
        "secret": totp_secret
    }

@app.post("/verify-totp")
async def verify_totp(verification: TOTPVerification):
    users = get_users()
    if verification.username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    
    totp = pyotp.TOTP(users[verification.username]["totp_secret"])
    if not totp.verify(verification.code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    
    return {"message": "Authentication successful"}

# Updated password routes
@app.get("/passwords/{app_username}/{service}")
async def get_passwords(app_username: str, service: str):
    users = get_users()
    if app_username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    return password_manager.get_password(app_username, service)

@app.post("/passwords/{app_username}")
async def add_password(app_username: str, entry: PasswordEntry):
    users = get_users()
    if app_username not in users:
        raise HTTPException(status_code=404, detail="User not found")
    
    password_manager.add_password(
        app_username=app_username,
        service=entry.service,
        service_username=entry.service_username,  # Use service_username instead of username
        password=entry.encrypted_password
    )
    return {"message": "Password added successfully"}
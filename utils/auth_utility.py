import os
import re
import uuid
from datetime import datetime, timezone

import bcrypt
import jwt
from bson import ObjectId


def generate_login_id(company_name: str, phone: str) -> str:
    # clean company name
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()

    # take last 2 digits of phone
    phone_suffix = phone[-2:]

    # add random suffix to avoid collisions
    unique = str(uuid.uuid4())[:3]

    return f"{clean_name}_{phone_suffix}_{unique}"


import secrets
import string

def generate_secure_password(length: int = 12) -> str:
    characters = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password

def hash_password(password: str) -> str:
    """Hash a password using bcrypt with 10 rounds"""
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def get_auth_dict(user_id,hashed_password,email_id)->dict:
    auth = {
        "_id": ObjectId(),
        "user_id": user_id,
        "email_id": email_id,
        "password_hash": hashed_password,
        "password_changed_at": datetime.now(timezone.utc)
    }
    return auth

def create_access_token(data: dict):
    SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    ALGORITHM = os.getenv("JWT_ALGORITHM")
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def get_decoded_jwt_token(token:str) -> dict:
    SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    ALGORITHM = os.getenv("JWT_ALGORITHM")
    return jwt.decode(token,SECRET_KEY,ALGORITHM)


def is_password_valid(password: str):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"

    return True, "Password is valid"


def is_email_valid(email: str):
    if len(email) < 5:
        return False, "Email is too short"

    email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    if not re.match(email_pattern, email):
        return False

    return True


def generate_unique_id() -> str:
    return str(uuid.uuid4())
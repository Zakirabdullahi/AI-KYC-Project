import hashlib
from datetime import datetime, timedelta
import jwt
from flask import request, jsonify
from functools import wraps
import models
from database import SessionLocal

SECRET_KEY = "bank_super_secret_key_2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours for dev purposes

def get_password_hash(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def create_access_token(data: dict, expires_delta=None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def wrap_db(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        db = SessionLocal()
        try:
            return f(*args, db=db, **kwargs)
        finally:
            db.close()
    return decorated

def require_auth(f):
    @wraps(f)
    @wrap_db
    def decorated(*args, db=None, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"detail": "Unauthorized"}), 401
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            user = db.query(models.User).filter(models.User.email == email).first()
            if not user:
                return jsonify({"detail": "User not found"}), 401
            request.current_user = user
        except:
            return jsonify({"detail": "Invalid token"}), 401
        return f(*args, db=db, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    @require_auth
    def decorated(*args, db=None, **kwargs):
        user = request.current_user
        if user.role != models.RoleEnum.admin.value:
            return jsonify({"detail": "Admin privileges required"}), 403
        return f(*args, db=db, **kwargs)
    return decorated

import hashlib
from datetime import datetime, timedelta, timezone
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
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=15)
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
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"detail": "Missing authorization header"}), 401
        
        try:
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            
            # Use leeway to account for clock drift on Vercel
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], leeway=60)
            email = payload.get("sub")
            if not email:
                print("AUTH ERROR: Token payload missing 'sub'")
                return jsonify({"detail": "Invalid token payload"}), 401
                
            user = db.query(models.User).filter(models.User.email == email).first()
            if not user:
                print(f"AUTH ERROR: User not found for email {email}")
                return jsonify({"detail": "User not found"}), 401
            request.current_user = user
        except jwt.ExpiredSignatureError:
            msg = "Token expired (clock skew or 24h limit reached)"
            print(f"AUTH ERROR: {msg}")
            return jsonify({"detail": msg}), 401
        except jwt.InvalidTokenError as e:
            msg = f"Invalid token: {str(e)}"
            print(f"AUTH ERROR: {msg}")
            return jsonify({"detail": msg}), 401
        except Exception as e:
            msg = f"Authentication failed: {str(e)}"
            print(f"AUTH ERROR: {msg}")
            return jsonify({"detail": msg}), 401

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

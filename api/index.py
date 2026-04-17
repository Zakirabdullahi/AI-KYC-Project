import sys
import os
import traceback

# Essential for Vercel: Add current directory to path so sibling modules are found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_cors import CORS

# Create the app object at top-level so Vercel's builder always find it
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

DEBUG_ERROR = None
db_mode = "Unknown"

try:
    import models
    import database
    import auth
    from banking import banking_bp
    from verification import verify_bp
    from admin import admin_bp
    
    app.register_blueprint(banking_bp, url_prefix='/api/banking')
    app.register_blueprint(verify_bp, url_prefix='/api/verify')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # Check mode
    db_mode = "Postgres" if database.SQLALCHEMY_DATABASE_URL.startswith("postgresql") else "SQLite"
    print(f"--- STARTUP: Horizon Bank API in {db_mode} mode ---")

except Exception as e:
    DEBUG_ERROR = traceback.format_exc()
    print("--- FATAL STARTUP ERROR ---")
    print(DEBUG_ERROR)
    db_mode = "Error"

from sqlalchemy import text
import uuid

@app.route("/health", methods=["GET"])
@auth.wrap_db
def health(db):
    if DEBUG_ERROR:
        return jsonify({"status": "error", "detail": "Startup failed", "traceback": DEBUG_ERROR}), 500
        
    db_status = "Connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"Disconnected: {str(e)}"
    
    return jsonify({
        "status": "ok", 
        "system": "Horizon Bank API v2.0",
        "database": db_status,
        "mode": db_mode
    })

@app.route("/api/setup", methods=["GET"])
@auth.wrap_db
def setup_database(db):
    """One-time route to ensure tables exist and admin user is created."""
    if DEBUG_ERROR:
        return jsonify({"detail": "Critical Startup Error", "traceback": DEBUG_ERROR}), 500
        
    try:
        import database
        import models
        models.Base.metadata.create_all(bind=database.engine)
        
        # Check if admin exists
        admin = db.query(models.User).filter(models.User.role == "admin").first()
        if not admin:
            admin_pwd = "horizon_admin_2026"
            new_admin = models.User(
                full_name="System Administrator",
                email="admin@horizon.com",
                hashed_password=auth.get_password_hash(admin_pwd),
                role="admin",
                verification_status="verified"
            )
            db.add(new_admin)
            db.commit()
            return jsonify({
                "message": "Database initialized and admin account created.",
                "admin_email": "admin@horizon.com",
                "admin_password": admin_pwd
            })
        return jsonify({"message": "Database already initialized. Admin exists."})
    except Exception as e:
        return jsonify({"detail": f"Setup failed: {str(e)}"}), 500

@app.route("/api/debug", methods=["GET"])
def debug():
    """Diagnostic route to check environment setup."""
    vars_to_check = ["POSTGRES_URL", "DATABASE_URL", "POSTGRES_PRISMA_URL", "VERCEL", "PORT"]
    env_status = {var: ("SET" if os.getenv(var) else "MISSING") for var in vars_to_check}
    
    return jsonify({
        "environment": env_status,
        "startup_error": DEBUG_ERROR,
        "db_mode": db_mode
    })

@app.errorhandler(Exception)
def handle_exception(e):
    # Log the detail for Vercel logs
    print(f"ERROR: {str(e)}")
    if hasattr(e, 'code'):
        return jsonify({"detail": str(e.description)}), e.code
    return jsonify({"detail": f"Internal Server Error: {str(e)}"}), 500

# ── Auth ─────────────────────────────────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
@auth.wrap_db
def register(db):
    if DEBUG_ERROR: return jsonify({"detail": "Backend in error state"}), 500
    data = request.json
    db_user = db.query(models.User).filter(models.User.email == data.get("email")).first()
    if db_user:
        return jsonify({"detail": "Email already registered"}), 400
    
    new_user = models.User(
        full_name=data.get("full_name"), 
        email=data.get("email"), 
        hashed_password=auth.get_password_hash(data.get("password")),
        phone=data.get("phone"),
        address=data.get("address")
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Provision checking account
    new_acc = models.Account(
        account_number=str(uuid.uuid4().hex[:10]).upper(), 
        balance=0.0, 
        account_type="checking", 
        user_id=new_user.id
    )
    db.add(new_acc)
    # Provision savings account
    sav_acc = models.Account(
        account_number=str(uuid.uuid4().hex[:10]).upper(), 
        balance=0.0, 
        account_type="savings", 
        user_id=new_user.id
    )
    db.add(sav_acc)
    db.commit()
    return jsonify({"message": "User registered successfully", "id": new_user.id})

@app.route("/api/auth/token", methods=["POST"])
@auth.wrap_db
def login(db):
    if DEBUG_ERROR: return jsonify({"detail": "Backend in error state"}), 500
    data = request.json
    email = data.get("email")
    pwd = data.get("password")
    
    # Verify tables exist by attempting to query
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
    except Exception as e:
        return jsonify({"detail": "Database Error: Tables may not be initialized. Please visit /api/setup first."}), 500

    if not user or user.hashed_password != auth.get_password_hash(pwd):
        return jsonify({"detail": "Incorrect email or password"}), 401
        
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    return jsonify({"access_token": access_token, "token_type": "bearer", "role": user.role})

# ── User Profile ─────────────────────────────────────────────────────────────────

@app.route("/api/users/me", methods=["GET"])
@auth.require_auth
def read_users_me(db):
    u = request.current_user
    return jsonify({
        "id": u.id,
        "full_name": u.full_name,
        "email": u.email,
        "phone": u.phone,
        "address": u.address,
        "role": u.role,
        "verification_status": u.verification_status,
        "created_at": u.created_at.isoformat() if u.created_at else None
    }), 200

# Other routes...
# (Keeping only essential ones for the demo to ensure index.py stays clean and builder-friendly)

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    if DEBUG_ERROR:
        return jsonify({"detail": "Startup Error", "traceback": DEBUG_ERROR}), 500
    return jsonify({"detail": f"Path / {path} not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002, debug=True)

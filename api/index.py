import sys
import os
import traceback

# Essential for Vercel: Add current directory to path so sibling modules are found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

DEBUG_ERROR = None

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    import jwt
    import models
    import database
    import auth
    from banking import banking_bp
    from verification import verify_bp
    from admin import admin_bp
    
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Check mode
    db_mode = "Postgres" if database.SQLALCHEMY_DATABASE_URL.startswith("postgresql") else "SQLite"
    print(f"--- STARTUP: Horizon Bank API in {db_mode} mode ---")

except Exception as e:
    DEBUG_ERROR = traceback.format_exc()
    print("--- FATAL IMPORT OR STARTUP ERROR ---")
    print(DEBUG_ERROR)
    from flask import Flask, jsonify
    app = Flask(__name__)
    @app.route("/api/debug", methods=["GET"])
    def debug_error():
        # Mask potentially sensitive data in traceback
        safe_trace = DEBUG_ERROR.replace(os.getenv("POSTGRES_URL", "---"), "POSTGRES_URL_HIDDEN")
        return jsonify({"detail": "Critical Startup Error", "traceback": safe_trace}), 500
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def catch_all(path):
        return jsonify({"detail": "Startup Error", "traceback": "Check /api/debug for details"}), 500
    # Stop further execution to prevent double-app definition issues
    # But Flask requires the 'app' variable to be available at the top level
    db_mode = "Error"

if db_mode != "Error":
    app.register_blueprint(banking_bp, url_prefix='/api/banking')
    app.register_blueprint(verify_bp, url_prefix='/api/verify')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

from sqlalchemy import text
import uuid

@app.route("/health", methods=["GET"])
@auth.wrap_db
def health(db):
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
    try:
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
        "database_url_masked": database.SQLALCHEMY_DATABASE_URL[:20] + "..." if database.SQLALCHEMY_DATABASE_URL else "NONE"
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
    data = request.json
    db_user = db.query(models.User).filter(models.User.email == data.get("email")).first()
    if db_user:
        return jsonify({"detail": "Email already registered"}), 400
    
    import uuid
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
    # Welcome notification
    notif = models.Notification(
        user_id=new_user.id,
        message=f"Welcome to Horizon Bank, {new_user.full_name}! Please complete KYC verification to unlock all features.",
        category="info"
    )
    db.add(notif)
    db.commit()
    return jsonify({"message": "User registered successfully", "id": new_user.id})

@app.route("/api/auth/token", methods=["POST"])
@auth.wrap_db
def login(db):
    data = request.json
    email = data.get("email")
    pwd = data.get("password")
    
    user = db.query(models.User).filter(models.User.email == email).first()
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

@app.route("/api/users/me/profile", methods=["PATCH"])
@auth.require_auth
def update_profile(db):
    u = request.current_user
    data = request.json
    if "full_name" in data and data["full_name"].strip():
        u.full_name = data["full_name"].strip()
    if "phone" in data:
        u.phone = data["phone"].strip()
    if "address" in data:
        u.address = data["address"].strip()
    db.commit()
    return jsonify({"message": "Profile updated successfully."}), 200

@app.route("/api/users/me/change-password", methods=["POST"])
@auth.require_auth
def change_password(db):
    u = request.current_user
    data = request.json
    current = data.get("current_password", "")
    new_pwd = data.get("new_password", "")
    if not new_pwd or len(new_pwd) < 6:
        return jsonify({"detail": "New password must be at least 6 characters."}), 400
    if u.hashed_password != auth.get_password_hash(current):
        return jsonify({"detail": "Current password is incorrect."}), 400
    u.hashed_password = auth.get_password_hash(new_pwd)
    notif = models.Notification(user_id=u.id, message="Your password was changed successfully.", category="alert")
    db.add(notif)
    db.commit()
    return jsonify({"message": "Password changed successfully."}), 200

# ── Notifications ─────────────────────────────────────────────────────────────────

@app.route("/api/notifications", methods=["GET"])
@auth.require_auth
def get_notifications(db):
    u = request.current_user
    notifs = db.query(models.Notification).filter(models.Notification.user_id == u.id).order_by(models.Notification.created_at.desc()).limit(30).all()
    return jsonify([{
        "id": n.id,
        "message": n.message,
        "category": n.category,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat()
    } for n in notifs]), 200

@app.route("/api/notifications/<int:notif_id>/read", methods=["PATCH"])
@auth.require_auth
def mark_notification_read(notif_id, db):
    u = request.current_user
    notif = db.query(models.Notification).filter(models.Notification.id == notif_id, models.Notification.user_id == u.id).first()
    if not notif:
        return jsonify({"detail": "Notification not found"}), 404
    notif.is_read = True
    db.commit()
    return jsonify({"message": "Marked as read"}), 200

@app.route("/api/notifications/read-all", methods=["PATCH"])
@auth.require_auth
def mark_all_read(db):
    u = request.current_user
    db.query(models.Notification).filter(models.Notification.user_id == u.id, models.Notification.is_read == False).update({"is_read": True})
    db.commit()
    return jsonify({"message": "All notifications marked as read"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002, debug=True)

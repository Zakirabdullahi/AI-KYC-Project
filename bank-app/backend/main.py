from flask import Flask, request, jsonify
import jwt
import models, database, auth
from banking import banking_bp
from verification import verify_bp
from admin import admin_bp

from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Create tables in the database (Safe for both SQLite and Postgres)
db_mode = "Postgres" if database.SQLALCHEMY_DATABASE_URL.startswith("postgres") else "SQLite"
print(f"--- STARTUP: Initializing {db_mode} database ---")
models.Base.metadata.create_all(bind=database.engine)

app.register_blueprint(banking_bp, url_prefix='/api/banking')
app.register_blueprint(verify_bp, url_prefix='/api/verify')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# ── Health ──────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "system": "Horizon Bank API v2.0"})

@app.errorhandler(Exception)
def handle_exception(e):
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

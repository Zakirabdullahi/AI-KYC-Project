from flask import Blueprint, request, jsonify
import models, auth

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/stats", methods=["GET"])
@auth.require_admin
def get_stats(db):
    total_users = db.query(models.User).filter(models.User.role == "customer").count()
    total_verified = db.query(models.User).filter(models.User.verification_status == "verified").count()
    total_pending = db.query(models.User).filter(models.User.verification_status == "pending").count()
    total_suspended = db.query(models.User).filter(models.User.verification_status == "suspended").count()
    total_rejected = db.query(models.User).filter(models.User.verification_status == "rejected").count()
    total_unverified = db.query(models.User).filter(models.User.verification_status == "unverified").count()
    total_transactions = db.query(models.Transaction).count()
    total_deposits = db.query(models.Transaction).filter(models.Transaction.type == "deposit").count()
    total_withdrawals = db.query(models.Transaction).filter(models.Transaction.type == "withdrawal").count()
    total_transfers = db.query(models.Transaction).filter(models.Transaction.type == "transfer").count()
    # Sum all account balances
    from sqlalchemy import func
    total_assets = db.query(func.sum(models.Account.balance)).scalar() or 0.0
    total_loans = db.query(func.sum(models.Loan.balance_remaining)).filter(models.Loan.status == "active").scalar() or 0.0

    return jsonify({
        "users": {"total": total_users, "verified": total_verified, "pending": total_pending, "suspended": total_suspended, "rejected": total_rejected, "unverified": total_unverified},
        "transactions": {"total": total_transactions, "deposits": total_deposits, "withdrawals": total_withdrawals, "transfers": total_transfers},
        "finances": {"total_assets_under_management": round(total_assets, 2), "total_outstanding_loans": round(total_loans, 2)}
    }), 200

@admin_bp.route("/users", methods=["GET"])
@auth.require_admin
def get_all_users(db):
    query_str = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    q = db.query(models.User)
    if query_str:
        like = f"%{query_str}%"
        q = q.filter((models.User.full_name.like(like)) | (models.User.email.like(like)))
    if status_filter:
        q = q.filter(models.User.verification_status == status_filter)

    users = q.order_by(models.User.created_at.desc()).all()
    safe_users = [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "verification_status": u.verification_status,
            "created_at": u.created_at.isoformat() if u.created_at else None
        } for u in users
    ]
    return jsonify(safe_users), 200

@admin_bp.route("/pending-verifications", methods=["GET"])
@auth.require_admin
def get_pending_verifications(db):
    users = db.query(models.User).filter(
        models.User.verification_status == models.VerificationStatusEnum.pending.value
    ).all()
    return jsonify([{"id": u.id, "full_name": u.full_name, "email": u.email} for u in users]), 200

@admin_bp.route("/verify-user/<int:user_id>", methods=["POST"])
@auth.require_admin
def decide_user_verification(user_id, db):
    data = request.json
    decision = data.get("decision")
    if decision not in ["verified", "rejected", "suspended", "pending"]:
        return jsonify({"detail": "Invalid decision."}), 400
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return jsonify({"detail": "User not found"}), 404
        
    user.verification_status = decision
    # Notify the user
    msg_map = {
        "verified": "Your account has been verified! You now have full access to all features.",
        "rejected": "Your KYC submission was rejected. Please resubmit with valid documents.",
        "suspended": "Your account has been suspended. Contact support for assistance.",
        "pending": "Your account status has been reset to pending review.",
    }
    notif = models.Notification(user_id=user.id, message=msg_map.get(decision, f"Account status updated to {decision}."), category="alert" if decision in ["rejected","suspended"] else "success")
    db.add(notif)
    db.commit()
    return jsonify({"message": f"User {user.email} marked as {decision}."}), 200

@admin_bp.route("/users/<int:user_id>", methods=["GET"])
@auth.require_admin
def get_user_details(user_id, db):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return jsonify({"detail": "User not found"}), 404
        
    accounts = [{"id": a.id, "account_number": a.account_number, "balance": a.balance, "account_type": a.account_type} for a in user.accounts]
    
    account_ids = [acc.id for acc in user.accounts]
    txs = db.query(models.Transaction).filter(
        (models.Transaction.from_account_id.in_(account_ids)) | 
        (models.Transaction.to_account_id.in_(account_ids))
    ).order_by(models.Transaction.timestamp.desc()).limit(10).all()
    
    recent_transactions = [{"id": t.id, "amount": t.amount, "type": t.type, "description": t.description, "timestamp": t.timestamp.isoformat()} for t in txs]
    loans = [{"id": l.id, "amount": l.amount, "balance_remaining": l.balance_remaining, "status": l.status, "monthly_payment": l.monthly_payment} for l in user.loans]
    
    return jsonify({
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "address": user.address,
        "role": user.role,
        "verification_status": user.verification_status,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "accounts": accounts,
        "recent_transactions": recent_transactions,
        "loans": loans
    }), 200

@admin_bp.route("/users/<int:user_id>/kyc-docs", methods=["GET"])
@auth.require_admin
def get_user_kyc(user_id, db):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return jsonify({"detail": "User not found"}), 404
    return jsonify({
        "front_doc": user.kyc_front_doc,
        "back_doc": user.kyc_back_doc,
        "selfie": user.kyc_selfie,
        "has_docs": bool(user.kyc_front_doc or user.kyc_back_doc or user.kyc_selfie)
    }), 200

@admin_bp.route("/users/<int:user_id>/adjust-balance", methods=["POST"])
@auth.require_admin
def admin_adjust_balance(user_id, db):
    data = request.json
    import uuid
    amount = float(data.get("amount", 0))
    operation = data.get("operation", "credit")  # "credit" or "debit"
    reason = data.get("reason", "Admin adjustment")
    account_type = data.get("account_type", "checking")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return jsonify({"detail": "User not found"}), 404
    if amount <= 0:
        return jsonify({"detail": "Amount must be positive."}), 400

    account = db.query(models.Account).filter(models.Account.user_id == user_id, models.Account.account_type == account_type).first()
    if not account:
        return jsonify({"detail": f"No {account_type} account found for this user."}), 404

    ref = "ADJ" + str(uuid.uuid4().hex[:8]).upper()
    if operation == "credit":
        account.balance += amount
        tx = models.Transaction(to_account_id=account.id, amount=amount, type="deposit", description=f"Admin Credit | {reason} | Ref: {ref}")
        notif_msg = f"A credit of ${amount:,.2f} was applied to your {account_type} account by administration. Reason: {reason}"
    else:
        if account.balance < amount:
            return jsonify({"detail": "Insufficient account balance for debit."}), 400
        account.balance -= amount
        tx = models.Transaction(from_account_id=account.id, amount=amount, type="withdrawal", description=f"Admin Debit | {reason} | Ref: {ref}")
        notif_msg = f"A debit of ${amount:,.2f} was applied to your {account_type} account by administration. Reason: {reason}"

    db.add(tx)
    notif = models.Notification(user_id=user.id, message=notif_msg, category="alert")
    db.add(notif)
    db.commit()
    return jsonify({"message": f"Balance {operation}ed by ${amount:.2f}. New balance: ${account.balance:.2f}"}), 200

# ── Admin Password Reset ────────────────────────────────────────────────────────

@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@auth.require_admin
def admin_reset_password(user_id, db):
    data = request.json
    new_password = data.get("new_password", "").strip()
    if not new_password or len(new_password) < 6:
        return jsonify({"detail": "Password must be at least 6 characters."}), 400

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return jsonify({"detail": "User not found."}), 404

    user.hashed_password = auth.get_password_hash(new_password)
    notif = models.Notification(
        user_id=user.id,
        message="Your account password has been reset by an administrator. If you did not request this, please contact support immediately.",
        category="alert"
    )
    db.add(notif)
    db.commit()
    return jsonify({"message": f"Password for {user.email} has been reset successfully."}), 200

# ── Delete KYC Documents ──────────────────────────────────────────────────────

@admin_bp.route("/users/<int:user_id>/kyc-docs", methods=["DELETE"])
@auth.require_admin
def delete_user_kyc_docs(user_id, db):
    """Permanently delete KYC documents for a user."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return jsonify({"detail": "User not found."}), 404

    docs = db.query(models.KycDocument).filter(models.KycDocument.user_id == user_id).first()
    if not docs:
        return jsonify({"detail": "No KYC documents found for this user."}), 404

    db.delete(docs)
    
    # Optionally reset user status to unverified if they were pending
    if user.verification_status == models.VerificationStatusEnum.pending.value:
        user.verification_status = models.VerificationStatusEnum.unverified.value

    db.commit()

    return jsonify({"message": "KYC documents permanently deleted."}), 200)

@admin_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@auth.require_admin
def update_user_role(user_id, db):
    """Change a user's role (promote to admin or demote to customer)."""
    data = request.json
    new_role = data.get("role")
    if new_role not in ["admin", "customer"]:
        return jsonify({"detail": "Invalid role."}), 400
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return jsonify({"detail": "User not found."}), 404
        
    # Prevent the last administrator from demoting themselves (optional safety check)
    current_admin = request.current_user
    if user.id == current_admin.id and new_role != "admin":
        return jsonify({"detail": "You cannot demote yourself. Another admin must do this."}), 400

    user.role = new_role
    db.commit()
    
    notif_msg = f"Your account role has been updated to {new_role.upper()}."
    notif = models.Notification(user_id=user.id, message=notif_msg, category="info")
    db.add(notif)
    db.commit()
    
    return jsonify({"message": f"User {user.email} is now an {new_role}."}), 200


@admin_bp.route("/transactions", methods=["GET"])
@auth.require_admin
def get_all_transactions(db):
    tx_type = request.args.get("type", "")
    q = db.query(models.Transaction)
    if tx_type:
        q = q.filter(models.Transaction.type == tx_type)
    txs = q.order_by(models.Transaction.timestamp.desc()).limit(200).all()
    return jsonify([{
        "id": t.id, 
        "amount": t.amount, 
        "type": t.type, 
        "description": t.description, 
        "timestamp": t.timestamp.isoformat(), 
        "from_account_id": t.from_account_id, 
        "to_account_id": t.to_account_id
    } for t in txs]), 200

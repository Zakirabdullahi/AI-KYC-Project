"""
verification.py — KYC verification endpoint with Smile ID integration
Flow:
  1. User submits: id_number, country, id_type, front_doc, back_doc, selfie
  2. If Smile ID is configured → run ID verification + biometric KYC automatically
  3. Auto-approve if confidence >= threshold, auto-reject if fraud/mismatch detected
  4. Fall back to "pending" (manual admin review) if Smile ID is not configured
"""
from flask import Blueprint, request, jsonify
import models, auth
from smile_id import (
    is_configured, verify_id_number, verify_biometric_kyc, get_supported_id_types
)

verify_bp = Blueprint("verify", __name__)


@verify_bp.route("/submit", methods=["POST"])
@auth.require_auth
def submit_verification(db):
    u = request.current_user

    if u.verification_status == models.VerificationStatusEnum.verified.value:
        return jsonify({"detail": "Account is already verified."}), 400
    if u.verification_status == models.VerificationStatusEnum.suspended.value:
        return jsonify({"detail": "Account is suspended. Contact support."}), 403

    data        = request.json
    id_number   = data.get("id_number", "").strip()
    country     = data.get("country", "KE").upper()
    id_type     = data.get("id_type", "NATIONAL_ID").upper()
    first_name  = data.get("first_name", u.full_name.split()[0] if u.full_name else "")
    last_name   = data.get("last_name", u.full_name.split()[-1] if u.full_name and " " in u.full_name else "")
    front_img   = data.get("front_doc_b64")
    back_img    = data.get("back_doc_b64")
    selfie_img  = data.get("selfie_image_b64")
    left_img    = data.get("selfie_image_left_b64")
    right_img   = data.get("selfie_image_right_b64")

    if not id_number or not selfie_img or not front_img or not back_img:
        return jsonify({"detail": "Missing required fields: id_number, selfie, front/back documents."}), 400

    # Store documents regardless of outcome
    u.kyc_front_doc = front_img
    u.kyc_back_doc  = back_img
    u.kyc_selfie    = selfie_img
    u.kyc_selfie_left = left_img
    u.kyc_selfie_right = right_img

    # ── Smile ID path ─────────────────────────────────────────────────────────
    if is_configured():
        # Step 1: ID number check against government database
        id_result = verify_id_number(
            id_number=id_number,
            country=country,
            id_type=id_type,
            first_name=first_name,
            last_name=last_name,
        )

        if "error" in id_result and not id_result.get("mock"):
            # Network/API error — fall back to pending
            u.verification_status = models.VerificationStatusEnum.pending.value
            db.commit()
            return jsonify({
                "status": "pending",
                "message": "ID check service temporarily unavailable. Your submission is queued for manual review.",
                "smile_id": {"error": id_result.get("error")}
            }), 200

        if not id_result["success"]:
            # ID not found or does not match — reject
            u.verification_status = models.VerificationStatusEnum.rejected.value
            notif = models.Notification(
                user_id=u.id,
                message=f"KYC Rejected: ID number could not be verified ({id_result.get('result_text', 'Not found')}). Please resubmit with a valid government ID.",
                category="alert"
            )
            db.add(notif)
            db.commit()
            return jsonify({
                "status": "rejected",
                "message": "ID number verification failed. The document could not be matched to any government record.",
                "smile_id": {
                    "result_code": id_result.get("result_code"),
                    "result_text": id_result.get("result_text"),
                }
            }), 200

        # Step 2: Biometric KYC — faces selfie against ID document
        bio_result = verify_biometric_kyc(
            id_number=id_number,
            selfie_b64=selfie_img,
            id_doc_b64=front_img,
            country=country,
            id_type=id_type,
            first_name=first_name,
            last_name=last_name,
        )

        confidence  = bio_result.get("confidence", 0)
        result_code = bio_result.get("result_code", "")

        if bio_result.get("success"):
            # High confidence face match → auto-approve
            u.verification_status = models.VerificationStatusEnum.verified.value
            notif = models.Notification(
                user_id=u.id,
                message=f"KYC Approved! Your identity has been automatically verified (confidence: {confidence:.1f}%). All banking features are now enabled.",
                category="success"
            )
            db.add(notif)
            db.commit()
            return jsonify({
                "status": "verified",
                "message": f"Identity automatically verified. Confidence: {confidence:.1f}%",
                "smile_id": {
                    "result_code": result_code,
                    "result_text": bio_result.get("result_text"),
                    "confidence": confidence,
                    "actions": bio_result.get("actions"),
                }
            }), 200

        # Confidence below threshold or face mismatch → reject
        u.verification_status = models.VerificationStatusEnum.rejected.value
        notif = models.Notification(
            user_id=u.id,
            message=f"KYC Rejected: Face match confidence too low ({confidence:.1f}%). Please resubmit with a clear selfie matching your ID photo.",
            category="alert"
        )
        db.add(notif)
        db.commit()
        return jsonify({
            "status": "rejected",
            "message": f"Biometric verification failed. Face match confidence ({confidence:.1f}%) is below the required threshold.",
            "smile_id": {
                "result_code": result_code,
                "result_text": bio_result.get("result_text"),
                "confidence": confidence,
            }
        }), 200

    # ── Fallback: No Smile ID → manual admin review ───────────────────────────
    # Dev shortcut: id_number starting with AUTO → instant approve for testing
    if id_number.upper().startswith("AUTO"):
        u.verification_status = models.VerificationStatusEnum.verified.value
        db.commit()
        return jsonify({"status": "verified", "message": "Auto-approved (dev mode)"}), 200
    if id_number.upper().startswith("REJECT"):
        u.verification_status = models.VerificationStatusEnum.rejected.value
        db.commit()
        return jsonify({"status": "rejected", "message": "Rejected (dev mode)"}), 200

    u.verification_status = models.VerificationStatusEnum.pending.value
    notif = models.Notification(
        user_id=u.id,
        message="Your KYC documents have been submitted and are awaiting admin review. You will be notified once verified.",
        category="info"
    )
    db.add(notif)
    db.commit()
    return jsonify({
        "status": "pending",
        "message": "Documents submitted. Awaiting admin review.",
        "smile_id_configured": False,
        "tip": "Add SMILE_PARTNER_ID + SMILE_API_KEY to .env to enable automatic verification."
    }), 200


@verify_bp.route("/status", methods=["GET"])
@auth.require_auth
def get_status(db):
    return jsonify({
        "status": request.current_user.verification_status,
        "smile_id_configured": is_configured(),
    }), 200


@verify_bp.route("/id-types", methods=["GET"])
def list_id_types():
    """Returns supported countries and ID types for the frontend dropdown."""
    country = request.args.get("country")
    return jsonify(get_supported_id_types(country)), 200

from flask import Blueprint, request, jsonify
import models, auth
import uuid, math

banking_bp = Blueprint("banking", __name__)

@banking_bp.route("/accounts", methods=["GET"])
@auth.require_auth
def get_accounts(db):
    u = request.current_user
    
    # Auto-provision savings account for existing/new users
    has_savings = any(a.account_type.lower() == "savings" for a in u.accounts)
    if not has_savings:
        import uuid
        new_acc = models.Account(
            account_number=str(uuid.uuid4().hex[:10]).upper(), 
            balance=0.0, 
            account_type="savings", 
            user_id=u.id
        )
        db.add(new_acc)
        db.commit()
        db.refresh(u)
        
    accs = [{"id": a.id, "account_number": a.account_number, "balance": a.balance, "account_type": a.account_type} for a in u.accounts]
    return jsonify(accs), 200

@banking_bp.route("/add-funds", methods=["POST"])
@auth.require_auth
def add_funds(db):
    u = request.current_user
    if u.verification_status == models.VerificationStatusEnum.suspended.value:
        return jsonify({"detail": "Account suspended. Contact support."}), 403
        
    data = request.json
    amt = float(data.get("amount", 0))
    account_id = data.get("account_id") # optional, defaults to checking
    payment_method = data.get("payment_method", "mpesa")
    phone = data.get("phone", "")

    if amt <= 0:
        return jsonify({"detail": "Amount must be positive."}), 400
        
    if account_id:
        src = db.query(models.Account).filter(models.Account.id == account_id, models.Account.user_id == u.id).first()
    else:
        src = db.query(models.Account).filter(models.Account.user_id == u.id, models.Account.account_type == "checking").first()
        
    if not src:
        return jsonify({"detail": "Account not found."}), 404
        
    # Simulate processing delay for STK Push / Card verification
    import time
    if payment_method == "mpesa":
        time.sleep(2.5)
        desc_label = f"M-PESA Deposit | {phone}"
    else:
        time.sleep(1.5)
        desc_label = "Card Deposit"

    src.balance += amt
    import uuid
    tx_code = "DEP" + str(uuid.uuid4().hex[:8]).upper()
    tx = models.Transaction(to_account_id=src.id, amount=amt, type="deposit", description=f"{desc_label} | Ref: {tx_code}")
    db.add(tx)
    db.commit()
    return jsonify({"message": "Funds added successfully", "new_balance": src.balance}), 200

@banking_bp.route("/withdraw", methods=["POST"])
@auth.require_auth
def withdraw_funds(db):
    u = request.current_user
    if u.verification_status == models.VerificationStatusEnum.suspended.value:
        return jsonify({"detail": "Account suspended. Contact support."}), 403
        
    data = request.json
    amt = float(data.get("amount", 0))
    account_id = data.get("account_id") # optional, defaults to checking

    if amt <= 0:
        return jsonify({"detail": "Amount must be positive."}), 400
        
    if account_id:
        src = db.query(models.Account).filter(models.Account.id == account_id, models.Account.user_id == u.id).first()
    else:
        src = db.query(models.Account).filter(models.Account.user_id == u.id, models.Account.account_type == "checking").first()
        
    if not src:
        return jsonify({"detail": "Account not found."}), 404
        
    if src.balance < amt:
        return jsonify({"detail": "Insufficient funds."}), 400
        
    src.balance -= amt
    import uuid
    tx_code = "WDL" + str(uuid.uuid4().hex[:8]).upper()
    tx = models.Transaction(from_account_id=src.id, amount=amt, type="withdrawal", description=f"ATM/External Withdrawal | Ref: {tx_code}")
    db.add(tx)
    db.commit()
    return jsonify({"message": "Withdrawal successful", "new_balance": src.balance}), 200

@banking_bp.route("/transactions", methods=["GET"])
@auth.require_auth
def get_history(db):
    u = request.current_user
    account_ids = [acc.id for acc in u.accounts]
    txs = db.query(models.Transaction).filter(
        (models.Transaction.from_account_id.in_(account_ids)) | 
        (models.Transaction.to_account_id.in_(account_ids))
    ).order_by(models.Transaction.timestamp.desc()).limit(50).all()
    res = [{"id": t.id, "amount": t.amount, "type": t.type, "description": t.description, "timestamp": t.timestamp.isoformat(), "from_account_id": t.from_account_id, "to_account_id": t.to_account_id} for t in txs]
    return jsonify(res), 200

@banking_bp.route("/transfer", methods=["POST"])
@auth.require_auth
def execute_transfer(db):
    u = request.current_user
    if u.verification_status == models.VerificationStatusEnum.suspended.value:
        return jsonify({"detail": "Account suspended. Contact support."}), 403
    if u.verification_status != models.VerificationStatusEnum.verified.value:
        return jsonify({"detail": "Account not verified. Transfer operations locked."}), 403
    
    data = request.json
    amt = float(data.get("amount", 0))
    if amt <= 0:
        return jsonify({"detail": "Amount must be positive."}), 400
        
    src = db.query(models.Account).filter(models.Account.user_id == u.id).first()
    if not src or src.balance < amt:
        return jsonify({"detail": "Insufficient funds or account not found."}), 400
        
    dest = db.query(models.Account).filter(models.Account.account_number == data.get("to_account_number")).first()
    if not dest:
        return jsonify({"detail": "Destination account not found."}), 404
        
    if src.id == dest.id:
        return jsonify({"detail": "Cannot transfer to same account."}), 400
        
    src.balance -= amt
    dest.balance += amt
    tx_code = "TRF" + str(uuid.uuid4().hex[:8]).upper()
    tx = models.Transaction(from_account_id=src.id, to_account_id=dest.id, amount=amt, type="transfer", description=data.get("description", f"Transfer {tx_code}"))
    db.add(tx)
    db.commit()
    return jsonify({"message": "Transfer successful", "new_balance": src.balance}), 200

# ── Loans ───────────────────────────────────────────────────────────────────────

@banking_bp.route("/loans", methods=["GET"])
@auth.require_auth
def get_loans(db):
    u = request.current_user
    loans = db.query(models.Loan).filter(models.Loan.user_id == u.id).order_by(models.Loan.created_at.desc()).all()
    result = [{
        "id": l.id,
        "amount": l.amount,
        "balance_remaining": l.balance_remaining,
        "interest_rate": l.interest_rate,
        "term_months": l.term_months,
        "monthly_payment": l.monthly_payment,
        "status": l.status,
        "purpose": l.purpose,
        "created_at": l.created_at.isoformat()
    } for l in loans]
    return jsonify(result), 200

@banking_bp.route("/loans/apply", methods=["POST"])
@auth.require_auth
def apply_loan(db):
    u = request.current_user
    if u.verification_status != models.VerificationStatusEnum.verified.value:
        return jsonify({"detail": "KYC verification required to apply for a loan."}), 403
    if u.verification_status == models.VerificationStatusEnum.suspended.value:
        return jsonify({"detail": "Account suspended."}), 403

    data = request.json
    amount = float(data.get("amount", 0))
    term_months = int(data.get("term_months", 12))
    purpose = data.get("purpose", "Personal")

    if amount <= 0 or amount > 10000000:
        return jsonify({"detail": "Loan amount must be between KSh 1 and KSh 10,000,000."}), 400
    if term_months not in [6, 12, 24, 36, 60]:
        return jsonify({"detail": "Term must be 6, 12, 24, 36, or 60 months."}), 400

    # Standard amortization formula: M = P[r(1+r)^n]/[(1+r)^n-1]
    annual_rate = 5.5
    r = annual_rate / 100 / 12
    n = term_months
    if r == 0:
        monthly = amount / n
    else:
        monthly = amount * (r * math.pow(1 + r, n)) / (math.pow(1 + r, n) - 1)
    monthly = round(monthly, 2)

    loan = models.Loan(
        user_id=u.id,
        amount=amount,
        balance_remaining=amount,
        interest_rate=annual_rate,
        term_months=term_months,
        monthly_payment=monthly,
        purpose=purpose
    )
    db.add(loan)

    # Credit the funds to user's checking account
    checking = db.query(models.Account).filter(models.Account.user_id == u.id, models.Account.account_type == "checking").first()
    if checking:
        checking.balance += amount
        tx_code = "LOAN" + str(uuid.uuid4().hex[:8]).upper()
        tx = models.Transaction(to_account_id=checking.id, amount=amount, type="deposit", description=f"Loan Disbursement | {purpose} | Ref: {tx_code}")
        db.add(tx)

    # Create notification
    notif = models.Notification(user_id=u.id, message=f"Loan of KSh {amount:,.2f} approved and disbursed to your checking account.", category="success")
    db.add(notif)

    db.commit()
    return jsonify({"message": "Loan approved and disbursed.", "monthly_payment": monthly, "interest_rate": annual_rate}), 200

@banking_bp.route("/loans/repay", methods=["POST"])
@auth.require_auth
def repay_loan(db):
    u = request.current_user
    if u.verification_status == models.VerificationStatusEnum.suspended.value:
        return jsonify({"detail": "Account suspended."}), 403

    data = request.json
    loan_id = data.get("loan_id")
    amount = float(data.get("amount", 0))

    loan = db.query(models.Loan).filter(models.Loan.id == loan_id, models.Loan.user_id == u.id).first()
    if not loan:
        return jsonify({"detail": "Loan not found."}), 404
    if loan.status != models.LoanStatusEnum.active.value:
        return jsonify({"detail": "Loan is already paid off or defaulted."}), 400

    src = db.query(models.Account).filter(models.Account.user_id == u.id, models.Account.account_type == "checking").first()
    if not src or src.balance < amount:
        return jsonify({"detail": "Insufficient funds for repayment."}), 400

    payment = min(amount, loan.balance_remaining)
    src.balance -= payment
    loan.balance_remaining -= payment
    if loan.balance_remaining <= 0.01:
        loan.balance_remaining = 0
        loan.status = models.LoanStatusEnum.paid.value

    tx_code = "RPAY" + str(uuid.uuid4().hex[:8]).upper()
    tx = models.Transaction(from_account_id=src.id, amount=payment, type="withdrawal", description=f"Loan Repayment | Loan #{loan.id} | Ref: {tx_code}")
    db.add(tx)
    db.commit()
    return jsonify({"message": f"Repayment of KSh {payment:,.2f} successful.", "balance_remaining": loan.balance_remaining, "status": loan.status}), 200

# ── Statements ──────────────────────────────────────────────────────────────────

@banking_bp.route("/statements", methods=["GET"])
@auth.require_auth
def get_statement(db):
    u = request.current_user
    import datetime as dt
    month = int(request.args.get("month", dt.datetime.utcnow().month))
    year = int(request.args.get("year", dt.datetime.utcnow().year))

    start = dt.datetime(year, month, 1)
    if month == 12:
        end = dt.datetime(year + 1, 1, 1)
    else:
        end = dt.datetime(year, month + 1, 1)

    account_ids = [acc.id for acc in u.accounts]
    txs = db.query(models.Transaction).filter(
        ((models.Transaction.from_account_id.in_(account_ids)) | (models.Transaction.to_account_id.in_(account_ids))),
        models.Transaction.timestamp >= start,
        models.Transaction.timestamp < end
    ).order_by(models.Transaction.timestamp.asc()).all()

    total_credits = sum(t.amount for t in txs if t.to_account_id in account_ids)
    total_debits = sum(t.amount for t in txs if t.from_account_id in account_ids)

    return jsonify({
        "period": {"month": month, "year": year, "label": start.strftime("%B %Y")},
        "accounts": [{"id": a.id, "account_number": a.account_number, "type": a.account_type, "balance": a.balance} for a in u.accounts],
        "summary": {"total_credits": round(total_credits, 2), "total_debits": round(total_debits, 2), "net": round(total_credits - total_debits, 2), "transaction_count": len(txs)},
        "transactions": [{"id": t.id, "type": t.type, "amount": t.amount, "description": t.description, "timestamp": t.timestamp.isoformat(), "is_credit": t.to_account_id in account_ids} for t in txs]
    }), 200


@banking_bp.route("/statements/pdf", methods=["GET"])
@auth.require_auth
def download_statement_pdf(db):
    """Generate and stream a PDF bank statement for the requested month/year."""
    u = request.current_user
    import datetime as dt
    import io
    from flask import make_response
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    month = int(request.args.get("month", dt.datetime.utcnow().month))
    year  = int(request.args.get("year",  dt.datetime.utcnow().year))

    start = dt.datetime(year, month, 1)
    end   = dt.datetime(year + 1, 1, 1) if month == 12 else dt.datetime(year, month + 1, 1)
    period_label = start.strftime("%B %Y")

    account_ids = [acc.id for acc in u.accounts]
    txs = db.query(models.Transaction).filter(
        ((models.Transaction.from_account_id.in_(account_ids)) | (models.Transaction.to_account_id.in_(account_ids))),
        models.Transaction.timestamp >= start,
        models.Transaction.timestamp < end
    ).order_by(models.Transaction.timestamp.asc()).all()

    total_credits = sum(t.amount for t in txs if t.to_account_id in account_ids)
    total_debits  = sum(t.amount for t in txs if t.from_account_id in account_ids)

    # ── Build PDF ──────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    elems  = []

    # Header
    header_style = ParagraphStyle("header", fontSize=20, fontName="Helvetica-Bold",
                                   textColor=colors.HexColor("#00a9e0"), spaceAfter=2)
    sub_style    = ParagraphStyle("sub", fontSize=10, textColor=colors.HexColor("#718096"), spaceAfter=14)
    label_style  = ParagraphStyle("label", fontSize=9, textColor=colors.HexColor("#a0aec0"))
    value_style  = ParagraphStyle("value", fontSize=11, fontName="Helvetica-Bold",
                                   textColor=colors.HexColor("#1a202c"))

    elems.append(Paragraph("HORIZON BANK", header_style))
    elems.append(Paragraph(f"Account Statement — {period_label}", sub_style))
    elems.append(Spacer(1, 4*mm))

    # Customer info
    info_data = [
        [Paragraph("Account Holder", label_style), Paragraph(u.full_name or "—", value_style)],
        [Paragraph("Email", label_style),           Paragraph(u.email or "—", value_style)],
        [Paragraph("Phone", label_style),           Paragraph(u.phone or "—", value_style)],
        [Paragraph("Statement Period", label_style), Paragraph(period_label, value_style)],
        [Paragraph("Generated On", label_style),    Paragraph(dt.datetime.utcnow().strftime("%d %b %Y %H:%M UTC"), value_style)],
    ]
    info_tbl = Table(info_data, colWidths=[45*mm, 120*mm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elems.append(info_tbl)
    elems.append(Spacer(1, 6*mm))

    # Account balances
    elems.append(Paragraph("Accounts", ParagraphStyle("ah", fontSize=12, fontName="Helvetica-Bold",
                                                        textColor=colors.HexColor("#1a202c"), spaceBefore=4, spaceAfter=4)))
    acc_rows = [["Account Number", "Type", "Balance (KSh)"]]
    for acc in u.accounts:
        acc_rows.append([acc.account_number, acc.account_type.capitalize(),
                         f"{acc.balance:,.2f}"])
    acc_tbl = Table(acc_rows, colWidths=[65*mm, 50*mm, 55*mm])
    acc_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), colors.HexColor("#00a9e0")),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ALIGN",        (2, 0), (2, -1), "RIGHT"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f9ff")]),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e0")),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    elems.append(acc_tbl)
    elems.append(Spacer(1, 6*mm))

    # Summary
    elems.append(Paragraph("Period Summary", ParagraphStyle("sh", fontSize=12, fontName="Helvetica-Bold",
                                                              textColor=colors.HexColor("#1a202c"), spaceBefore=4, spaceAfter=4)))
    summary_rows = [
        ["Total Credits",  f"KSh {total_credits:,.2f}"],
        ["Total Debits",   f"KSh {total_debits:,.2f}"],
        ["Net",            f"KSh {total_credits - total_debits:,.2f}"],
        ["Transactions",   str(len(txs))],
    ]
    sum_tbl = Table(summary_rows, colWidths=[65*mm, 75*mm])
    sum_tbl.setStyle(TableStyle([
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ALIGN",         (1, 0), (1, -1), "RIGHT"),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.white, colors.HexColor("#f0f9ff")]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        # Colour the net row
        ("TEXTCOLOR",     (0, 2), (-1, 2), colors.HexColor("#2f855a") if total_credits >= total_debits else colors.HexColor("#e53e3e")),
        ("FONTNAME",      (0, 2), (-1, 2), "Helvetica-Bold"),
    ]))
    elems.append(sum_tbl)
    elems.append(Spacer(1, 6*mm))

    # Transactions table
    elems.append(Paragraph("Transaction History", ParagraphStyle("th", fontSize=12, fontName="Helvetica-Bold",
                                                                   textColor=colors.HexColor("#1a202c"), spaceBefore=4, spaceAfter=4)))
    if not txs:
        elems.append(Paragraph("No transactions in this period.", sub_style))
    else:
        tx_rows = [["Date", "Type", "Description", "Amount (KSh)", "Flow"]]
        for t in txs:
            is_credit = t.to_account_id in account_ids
            desc = (t.description or "System Transaction").split("|")[0].strip()
            tx_rows.append([
                t.timestamp.strftime("%d/%m/%Y"),
                t.type.capitalize(),
                desc[:45],
                f"{t.amount:,.2f}",
                "CR" if is_credit else "DR",
            ])
        tx_tbl = Table(tx_rows, colWidths=[25*mm, 22*mm, 80*mm, 30*mm, 15*mm])
        row_styles = [
            ("BACKGROUND",   (0, 0), (-1, 0), colors.HexColor("#1a202c")),
            ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
            ("ALIGN",        (3, 0), (4, -1), "RIGHT"),
            ("GRID",         (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e0")),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ]
        # Colour credit rows green, debit rows red
        for i, t in enumerate(txs, start=1):
            is_credit = t.to_account_id in account_ids
            clr = colors.HexColor("#f0fff4") if is_credit else colors.HexColor("#fff5f5")
            row_styles.append(("BACKGROUND", (0, i), (-1, i), clr))
            flow_color = colors.HexColor("#276749") if is_credit else colors.HexColor("#9b2c2c")
            row_styles.append(("TEXTCOLOR", (4, i), (4, i), flow_color))
            row_styles.append(("FONTNAME",  (4, i), (4, i), "Helvetica-Bold"))
        tx_tbl.setStyle(TableStyle(row_styles))
        elems.append(tx_tbl)

    # Footer
    elems.append(Spacer(1, 8*mm))
    elems.append(Paragraph("This is a computer-generated statement and requires no signature.",
                            ParagraphStyle("footer", fontSize=7, textColor=colors.HexColor("#a0aec0"),
                                           alignment=TA_CENTER)))

    doc.build(elems)
    buf.seek(0)

    fname = f"Horizon_Statement_{period_label.replace(' ', '_')}.pdf"
    response = make_response(buf.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{fname}"'
    return response


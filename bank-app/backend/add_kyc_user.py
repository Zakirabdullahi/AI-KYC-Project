from database import SessionLocal
import models
import uuid
from auth import get_password_hash

db = SessionLocal()

print("Creating/fetching a customer to place in the KYC queue...")

# Let's find a customer who isn't already pending/verified
user = db.query(models.User).filter(
    models.User.role == "customer",
    models.User.verification_status != "pending"
).first()

if not user:
    print("No existing unverified customer found. Creating a new dummy user: johndoe@example.com")
    user = models.User(
        full_name="John Doe",
        email="johndoe@example.com",
        phone="+1234567890",
        address="123 Verification St",
        hashed_password=get_password_hash("password123"),
        role="customer"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Provision checking account
    new_acc = models.Account(
        account_number=str(uuid.uuid4().hex[:10]).upper(), 
        balance=50.0, 
        account_type="checking", 
        user_id=user.id
    )
    db.add(new_acc)
    db.commit()

# Set their status
user.verification_status = "pending"
# Set dummy KYC documents so the Admin dashboard can load them
# Assuming the system accepts base64 prefixes or simple URLs. If it just loads string paths from DB, we can put dummy placeholders.
# Often if it's base64, leaving it as a normal distinct string like "data:image/png;base64,iVBORw0KGgo..." is safer so it doesn't break image rendering. We'll use a small red dot base64 as dummy images.

dummy_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
user.kyc_front_doc = dummy_b64
user.kyc_back_doc = dummy_b64
user.kyc_selfie = dummy_b64
user.kyc_selfie_left = dummy_b64
user.kyc_selfie_right = dummy_b64

db.commit()
print(f"Success! The user {user.full_name} ({user.email}) has been placed in the pending verification queue.")

db.close()

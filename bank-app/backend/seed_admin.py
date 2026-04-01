from database import SessionLocal
import models
import auth
import uuid

def create_admin():
    db = SessionLocal()
    
    # Check if admin already exists
    existing_admin = db.query(models.User).filter(models.User.email == "admin@horizonbank.com").first()
    if existing_admin:
        print("Admin already exists!")
        return
        
    # Create Admin User
    admin_user = models.User(
        full_name="System Administrator",
        email="admin@horizonbank.com",
        hashed_password=auth.get_password_hash("AdminSecure2026!"),
        role=models.RoleEnum.admin.value,
        verification_status=models.VerificationStatusEnum.verified.value
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    # Create a checking account for the admin
    new_acc = models.Account(
        account_number=str(uuid.uuid4().hex[:10]).upper(),
        balance=1000000.0,
        account_type="checking",
        user_id=admin_user.id
    )
    db.add(new_acc)
    db.commit()
    
    print("Admin created successfully!")
    db.close()

if __name__ == "__main__":
    create_admin()

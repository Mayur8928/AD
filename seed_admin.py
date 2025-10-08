# backend/seed_admin.py
# Script to create admin user for testing
import sys
from .auth import seed_admin_user

if __name__ == "__main__":
    email = "admin@skillsync.local"
    password = "admin123"
    
    if len(sys.argv) > 1:
        email = sys.argv[1]
    if len(sys.argv) > 2:
        password = sys.argv[2]
    
    seed_admin_user(email=email, password=password, full_name="Admin User")
    print("\n✅ Admin user created successfully!")
    print(f"📧 Email: {email}")
    print(f"🔑 Password: {password}")
    print("\nYou can now login at http://localhost:5173/login")


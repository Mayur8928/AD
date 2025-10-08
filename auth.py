# backend/auth.py
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt

# JWT Configuration
SECRET_KEY = "skillsync-secret-key-change-in-production"  # In production, use env variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

# Database path
AUTH_DB_PATH = "auth.db"

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ============= Database Initialization =============
def init_auth_db():
    """Initialize auth.db with users and user_files tables"""
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    
    # Users table with role support
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        sap_no TEXT UNIQUE,
        full_name TEXT,
        role TEXT CHECK(role IN ('student','admin')) DEFAULT 'student',
        created_at TEXT DEFAULT (DATETIME('now'))
    )
    """)
    
    # User files metadata table
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        file_type TEXT NOT NULL,
        filename TEXT,
        uploaded_at TEXT DEFAULT (DATETIME('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

# Initialize on import
init_auth_db()

# ============= Helper Functions =============
def get_password_hash(password: str) -> str:
    """Hash a password for storing"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email from auth.db"""
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, email, password_hash, sap_no, full_name, role, created_at FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "email": row[1],
            "password_hash": row[2],
            "sap_no": row[3],
            "full_name": row[4],
            "role": row[5],
            "created_at": row[6]
        }
    return None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID from auth.db"""
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, email, sap_no, full_name, role, created_at FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "email": row[1],
            "sap_no": row[2],
            "full_name": row[3],
            "role": row[4],
            "created_at": row[5]
        }
    return None

# ============= Auth Dependencies =============
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token.
    Usage: current_user = Depends(get_current_user)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency to require admin role.
    Usage: current_user = Depends(require_admin)
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# ============= API Endpoints =============
@router.post("/signup")
async def signup(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    sap_no: str = Form(None)
):
    """
    Student signup endpoint.
    Creates a new user account with student role.
    """
    # Validate email doesn't exist
    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check SAP number uniqueness if provided
    if sap_no:
        conn = sqlite3.connect(AUTH_DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE sap_no = ?", (sap_no,))
        if c.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="SAP number already registered")
        conn.close()
    
    # Hash password and create user
    password_hash = get_password_hash(password)
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (email, password_hash, full_name, sap_no, role) VALUES (?, ?, ?, ?, 'student')",
        (email, password_hash, full_name, sap_no)
    )
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    
    return {
        "ok": True,
        "user_id": user_id,
        "message": "User created successfully"
    }

@router.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...)
):
    """
    Login endpoint for both students and admins.
    Returns JWT access token.
    """
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"user_id": user["id"], "email": user["email"], "role": user["role"]}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "sap_no": user["sap_no"],
            "role": user["role"]
        }
    }

@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current logged-in user details.
    Protected endpoint that requires valid JWT token.
    """
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "sap_no": current_user["sap_no"],
        "role": current_user["role"],
        "created_at": current_user["created_at"]
    }

# ============= Admin Seed Function =============
def seed_admin_user(email: str = "admin@skillsync.local", password: str = "admin123", full_name: str = "Admin"):
    """
    Seed function to create an admin user for testing.
    Call this manually or via a separate script.
    """
    if get_user_by_email(email):
        print(f"Admin user {email} already exists")
        return
    
    password_hash = get_password_hash(password)
    conn = sqlite3.connect(AUTH_DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (email, password_hash, full_name, role) VALUES (?, ?, ?, 'admin')",
        (email, password_hash, full_name)
    )
    conn.commit()
    conn.close()
    print(f"Admin user created: {email} / {password}")

# Seed admin on first run (optional - comment out in production)
if __name__ == "__main__":
    seed_admin_user()


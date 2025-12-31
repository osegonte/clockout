from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings - Read from environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "some-random-secret-key-here")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

print(f"🔑 Security initialized with SECRET_KEY: {SECRET_KEY[:10]}...")
print(f"🔑 Algorithm: {ALGORITHM}")
print(f"🔑 Token expiry: {ACCESS_TOKEN_EXPIRE_MINUTES} minutes")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"⚠️ Password verification error: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password for storing.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing token payload (sub, user_id, role, etc.)
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        print(f"❌ Error creating JWT token: {str(e)}")
        raise


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: The JWT token string to decode
    
    Returns:
        Dictionary containing the token payload if valid, None otherwise
    """
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check if token has expired
        exp = payload.get("exp")
        if exp:
            if datetime.utcnow().timestamp() > exp:
                print("⚠️ Token has expired")
                return None
        
        return payload
    
    except JWTError as e:
        print(f"⚠️ JWT Error: {str(e)}")
        print(f"🔍 Using SECRET_KEY: {SECRET_KEY[:10]}...")
        print(f"🔍 Using ALGORITHM: {ALGORITHM}")
        return None
    
    except Exception as e:
        print(f"❌ Unexpected error decoding token: {str(e)}")
        return None


def create_password_reset_token(email: str) -> str:
    """
    Create a password reset token.
    """
    delta = timedelta(hours=1)  # Reset token expires in 1 hour
    return create_access_token(
        data={"sub": email, "type": "password_reset"},
        expires_delta=delta
    )


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify password reset token and return email if valid.
    """
    payload = decode_access_token(token)
    
    if not payload:
        return None
    
    token_type = payload.get("type")
    if token_type != "password_reset":
        return None
    
    email = payload.get("sub")
    return email
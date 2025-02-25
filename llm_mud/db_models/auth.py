"""Authentication utilities."""
import datetime
import jwt
import os
from typing import Optional, Any, Dict

from .users import User
from .db import get_session

# Use environment variable or set a default secret
JWT_SECRET = os.environ.get('JWT_SECRET', 'development_secret_key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION = 24 * 60 * 60  # 24 hours in seconds


def create_access_token(data: Dict[str, Any], expires_delta: Optional[int] = None) -> str:
    """Create a new JWT token."""
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        seconds=expires_delta or JWT_EXPIRATION
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a JWT token and return its payload if valid."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


async def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password."""
    session = get_session()
    try:
        user = session.query(User).filter(User.username == username).first()
        if user and user.verify_password(password):
            return user
        return None
    finally:
        session.close()


async def get_user_by_token(token: str) -> Optional[User]:
    """Get a user by their token."""
    payload = verify_token(token)
    if payload is None:
        return None
        
    username = payload.get("sub")
    if username is None:
        return None
        
    session = get_session()
    try:
        return session.query(User).filter(User.username == username).first()
    finally:
        session.close()
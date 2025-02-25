"""User database models."""

import datetime
import bcrypt
from sqlalchemy import Column, Integer, String, DateTime

from .db import Base


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    @classmethod
    def create(cls, username: str, password: str) -> "User":
        """Create a new user with hashed password."""
        # Hash the password with bcrypt
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

        return cls(username=username, password_hash=password_hash)

    def verify_password(self, password: str) -> bool:
        """Verify the provided password against the stored hash."""
        password_bytes = password.encode("utf-8")
        stored_hash = self.password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, stored_hash)

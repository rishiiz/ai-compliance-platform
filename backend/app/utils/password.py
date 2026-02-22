"""Password hashing and verification using bcrypt."""

import bcrypt


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    # bcrypt has a 72-byte limit; pass through as-is for normal-length passwords
    data = password.encode("utf-8")
    if len(data) > 72:
        data = data[:72]
    return bcrypt.hashpw(data, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        data = plain.encode("utf-8")
        if len(data) > 72:
            data = data[:72]
        return bcrypt.checkpw(data, hashed.encode("utf-8"))
    except Exception:
        return False

import uuid
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional
from app.database.mongodb import Database
from app.models.user import UserCreate, UserInDB
from fastapi import Request

# Password hashing - using a more specific configuration for bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# JWT settings
SECRET_KEY = "YOUR_SECRET_KEY"  # Change this in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def authenticate_user(username: str, password: str):
    db = Database.db
    user = await db.users.find_one({"username": username})
    if not user:
        return False

    # Add additional check to handle potentially malformed hashes
    if "password_hash" not in user or not user["password_hash"]:
        return False

    if not verify_password(password, user["password_hash"]):
        return False
    # Check if the account is locked (is_active = 0)
    if user.get("is_active", 1) == 0:
        return "locked"  # Special return value for locked accounts
    return user


async def create_user(user: UserCreate):
    db = Database.db
    # Check if username exists
    if await db.users.find_one({"username": user.username}):
        return None

    # Get next user ID
    last_user = await db.users.find_one(sort=[("user_id", -1)])
    # next_user_id = 1 if not last_user else last_user["user_id"] + 1
    next_user_id = uuid.uuid4().int

    # Create user document
    user_dict = user.dict()
    hashed_password = get_password_hash(user_dict.pop("password"))

    user_in_db = UserInDB(**user_dict, user_id=next_user_id, password_hash=hashed_password)

    # Insert into database
    result = await db.users.insert_one(user_in_db.dict())
    return await db.users.find_one({"_id": result.inserted_id})


async def get_current_user(request: Request):
    cookie_authorization = request.cookies.get("access_token")
    if not cookie_authorization:
        return None

    try:
        token_type, token = cookie_authorization.split()
        if token_type.lower() != "bearer":
            return None

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None
    except (JWTError, ValueError):
        return None

    db = Database.db
    user = await db.users.find_one({"username": username})

    if user is None:
        return None

    return user

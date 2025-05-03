from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    name: str
    role: str  # 'student', 'teacher', 'admin'
    grade: Optional[str] = None  # For students
    organization: Optional[str] = None  # For club/organization members

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    user_id: int
    password_hash: str
    is_active: int = 1
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    has_profile_image: bool = False  # Indicates if the user has a profile image

class UserResponse(UserBase):
    user_id: int
    created_at: str
    is_active: int

    class Config:
        orm_mode = True

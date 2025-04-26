import asyncio
from datetime import datetime
from app.database.mongodb import Database
from app.services.auth import get_password_hash

async def create_admin_user(username: str, password: str, name: str = "System Admin"):
    """Create an admin user in the database."""
    await Database.connect_to_database()
    
    # Check if user already exists
    existing_user = await Database.db.users.find_one({"username": username})
    if existing_user:
        print(f"User {username} already exists")
        return False
    
    # Get next user ID
    last_user = await Database.db.users.find_one(sort=[("user_id", -1)])
    next_user_id = 1 if not last_user else last_user["user_id"] + 1
    
    # Create admin user
    admin_user = {
        "username": username,
        "password_hash": get_password_hash(password),
        "role": "admin",
        "name": name,
        "grade": None,
        "organization": "School Administration",
        "is_active": 1,
        "created_at": datetime.now().isoformat(),
        "user_id": next_user_id
    }
    
    # Insert into database
    result = await Database.db.users.insert_one(admin_user)
    
    if result.inserted_id:
        print(f"Admin user created successfully: {username}")
        return True
    else:
        print("Failed to create admin user")
        return False
    
    await Database.close_database_connection()

# Run this script to create an admin user
if __name__ == "__main__":
    asyncio.run(create_admin_user("admin", "admin123"))

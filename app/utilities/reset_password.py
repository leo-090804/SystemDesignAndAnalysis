from app.database.mongodb import Database
from app.services.auth import get_password_hash

async def reset_user_password(username: str, new_password: str):
    """Reset a user's password in the database."""
    await Database.connect_to_database()
    
    # Generate hash for new password
    password_hash = get_password_hash(new_password)
    
    # Update user in database
    result = await Database.db.users.update_one(
        {"username": username},
        {"$set": {"password_hash": password_hash}}
    )
    
    if result.modified_count == 1:
        print(f"Password reset successful for user: {username}")
        return True
    else:
        print(f"User not found: {username}")
        return False
    
    await Database.close_database_connection()

# Example usage (uncomment to use)
# if __name__ == "__main__":
#     asyncio.run(reset_user_password("admin", "new_password"))

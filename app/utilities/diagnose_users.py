import asyncio
from app.database.mongodb import Database

async def diagnose_users():
    """Check for users with missing or malformed password hashes."""
    await Database.connect_to_database()
    
    users = await Database.db.users.find({}).to_list(length=100)
    
    print(f"Total users found: {len(users)}")
    
    problematic_users = []
    for user in users:
        if "password_hash" not in user or not user["password_hash"]:
            problematic_users.append({
                "username": user.get("username"),
                "user_id": user.get("user_id"),
                "issue": "Missing password hash"
            })
        elif not user["password_hash"].startswith("$2"):  # Bcrypt hashes start with $2
            problematic_users.append({
                "username": user.get("username"),
                "user_id": user.get("user_id"),
                "issue": "Not a bcrypt hash",
                "hash_prefix": user["password_hash"][:5] + "..."
            })
    
    if problematic_users:
        print("\nProblematic users found:")
        for user in problematic_users:
            print(f"- Username: {user['username']}, ID: {user['user_id']}, Issue: {user['issue']}")
        print("\nUse reset_password.py to fix these users.")
    else:
        print("\nNo problematic users found.")
    
    await Database.close_database_connection()

if __name__ == "__main__":
    asyncio.run(diagnose_users())

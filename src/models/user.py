"""
User model class for the School Item Exchange/Donation Application
"""

import bcrypt
from datetime import datetime

class User:
    def __init__(self, db_connection):
        """Initialize User model with database connection"""
        self.conn = db_connection
        self.cursor = self.conn.cursor()
        
    def create_user(self, username, password, email, full_name, role, school_id=None, profile_picture=None):
        """Create a new user account"""
        try:
            # Check if username or email already exist
            self.cursor.execute(
                "SELECT COUNT(*) FROM User WHERE username = ? OR email = ?",
                (username, email)
            )
            if self.cursor.fetchone()[0] > 0:
                return False, "Username or email already exists"
            
            # Hash the password
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Insert new user
            self.cursor.execute(
                """INSERT INTO User 
                   (username, password, email, full_name, role, school_id, profile_picture) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (username, hashed.decode('utf-8'), email, full_name, role, school_id, profile_picture)
            )
            self.conn.commit()
            return True, "User created successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error creating user: {str(e)}"
    
    def authenticate(self, username, password):
        """Authenticate user with username and password"""
        try:
            self.cursor.execute(
                "SELECT user_id, password, role FROM User WHERE username = ?",
                (username,)
            )
            user = self.cursor.fetchone()
            
            if not user:
                return False, "Invalid username or password", None
            
            user_id, stored_hash, role = user
            
            # Verify password
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                # Update last login time
                self.cursor.execute(
                    "UPDATE User SET last_login = ? WHERE user_id = ?",
                    (datetime.now(), user_id)
                )
                self.conn.commit()
                return True, "Authentication successful", {"user_id": user_id, "role": role}
            else:
                return False, "Invalid username or password", None
        except Exception as e:
            return False, f"Authentication error: {str(e)}", None
    
    def get_user_by_id(self, user_id):
        """Get user information by ID"""
        try:
            self.cursor.execute(
                """SELECT user_id, username, email, full_name, role, school_id, 
                   created_at, last_login, profile_picture 
                   FROM User WHERE user_id = ?""",
                (user_id,)
            )
            user = self.cursor.fetchone()
            
            if not user:
                return None
            
            return {
                'user_id': user[0],
                'username': user[1],
                'email': user[2],
                'full_name': user[3],
                'role': user[4],
                'school_id': user[5],
                'created_at': user[6],
                'last_login': user[7],
                'profile_picture': user[8]
            }
        except Exception as e:
            print(f"Error fetching user: {str(e)}")
            return None
    
    def update_user(self, user_id, **kwargs):
        """Update user information"""
        try:
            # Build update query dynamically based on provided fields
            fields = []
            values = []
            
            allowed_fields = ['email', 'full_name', 'school_id', 'profile_picture']
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    fields.append(f"{field} = ?")
                    values.append(value)
            
            if not fields:
                return False, "No valid fields to update"
            
            # Add user_id to values
            values.append(user_id)
            
            # Execute update query
            self.cursor.execute(
                f"UPDATE User SET {', '.join(fields)} WHERE user_id = ?",
                tuple(values)
            )
            self.conn.commit()
            return True, "User updated successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error updating user: {str(e)}"
    
    def change_password(self, user_id, current_password, new_password):
        """Change user password"""
        try:
            # Get current password hash
            self.cursor.execute(
                "SELECT password FROM User WHERE user_id = ?",
                (user_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "User not found"
            
            stored_hash = result[0]
            
            # Verify current password
            if not bcrypt.checkpw(current_password.encode('utf-8'), stored_hash.encode('utf-8')):
                return False, "Current password is incorrect"
            
            # Hash and update new password
            new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            
            self.cursor.execute(
                "UPDATE User SET password = ? WHERE user_id = ?",
                (new_hash.decode('utf-8'), user_id)
            )
            self.conn.commit()
            return True, "Password changed successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error changing password: {str(e)}"
    
    def delete_user(self, user_id):
        """Delete a user account"""
        try:
            # Check if user exists
            self.cursor.execute(
                "SELECT COUNT(*) FROM User WHERE user_id = ?",
                (user_id,)
            )
            if self.cursor.fetchone()[0] == 0:
                return False, "User not found"
            
            # Delete user
            self.cursor.execute(
                "DELETE FROM User WHERE user_id = ?",
                (user_id,)
            )
            self.conn.commit()
            return True, "User deleted successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error deleting user: {str(e)}"
    
    def get_all_users(self, role=None, limit=50, offset=0):
        """Get all users, optionally filtered by role"""
        try:
            query = """
                SELECT user_id, username, email, full_name, role, school_id, 
                created_at, last_login
                FROM User
            """
            params = []
            
            if role:
                query += " WHERE role = ?"
                params.append(role)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            self.cursor.execute(query, tuple(params))
            users = self.cursor.fetchall()
            
            result = []
            for user in users:
                result.append({
                    'user_id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'full_name': user[3],
                    'role': user[4],
                    'school_id': user[5],
                    'created_at': user[6],
                    'last_login': user[7]
                })
            
            return result
        except Exception as e:
            print(f"Error fetching users: {str(e)}")
            return []
    
    def change_user_role(self, user_id, new_role):
        """Change user role (admin only)"""
        if new_role not in ['student', 'teacher', 'moderator', 'admin']:
            return False, "Invalid role"
        
        try:
            self.cursor.execute(
                "UPDATE User SET role = ? WHERE user_id = ?",
                (new_role, user_id)
            )
            self.conn.commit()
            return True, f"User role changed to {new_role}"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error changing user role: {str(e)}"
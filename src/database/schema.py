"""
Database schema and initialization for School Item Exchange/Donation Application
"""

import sqlite3

class DatabaseManager:
    def __init__(self, db_path='school_exchange_app.db'):
        """Initialize database connection and create tables if they don't exist"""
        self.db_path = db_path
        self.conn = self._create_connection()
        if self.conn:
            self._create_tables()

    def _create_connection(self):
        """Create a database connection to SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return None

    def _create_tables(self):
        """Create all required tables in the database"""
        try:
            cursor = self.conn.cursor()
            
            # User table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS User (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                role VARCHAR(20) NOT NULL CHECK (role IN ('student', 'teacher', 'moderator', 'admin')),
                school_id VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                profile_picture VARCHAR(255)
            )
            ''')
            
            # Create Category table early since it doesn't depend on others
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Category (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL UNIQUE,
                description TEXT,
                is_active BOOLEAN DEFAULT 1
            )
            ''')

            # Event table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Event (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(100) NOT NULL,
                description TEXT,
                target DECIMAL(10, 2),
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                status VARCHAR(20) NOT NULL CHECK (status IN ('upcoming', 'active', 'completed', 'cancelled')),
                organizer_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                image_path VARCHAR(255),
                FOREIGN KEY (organizer_id) REFERENCES User(user_id)
            )
            ''')
            
            # Item table (depends on Event)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Item (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(100) NOT NULL,
                description TEXT,
                category VARCHAR(50) NOT NULL,
                condition VARCHAR(20) NOT NULL CHECK (condition IN ('new', 'like_new', 'good', 'fair', 'poor')),
                price DECIMAL(10, 2),
                status VARCHAR(20) NOT NULL CHECK (status IN ('draft', 'pending', 'approved', 'sold', 'exchanged', 'donated')),
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_id INTEGER,
                exchange_preferences TEXT,
                FOREIGN KEY (user_id) REFERENCES User(user_id),
                FOREIGN KEY (event_id) REFERENCES Event(event_id)
            )
            ''')
            
            # TransactionRecord table (renamed from "Transaction" to avoid reserved keyword)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS TransactionRecord (
                txn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                buyer_id INTEGER,
                item_id INTEGER NOT NULL,
                event_id INTEGER,
                type VARCHAR(20) NOT NULL CHECK (type IN ('sale', 'exchange', 'donation', 'event_contribution')),
                amount DECIMAL(10, 2),
                fee DECIMAL(10, 2) DEFAULT 0.00,
                status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'completed', 'cancelled')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (seller_id) REFERENCES User(user_id),
                FOREIGN KEY (buyer_id) REFERENCES User(user_id),
                FOREIGN KEY (item_id) REFERENCES Item(item_id),
                FOREIGN KEY (event_id) REFERENCES Event(event_id)
            )
            ''')
            
            # Message table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Message (
                msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                txn_id INTEGER,
                content TEXT NOT NULL,
                read_status BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES User(user_id),
                FOREIGN KEY (receiver_id) REFERENCES User(user_id),
                FOREIGN KEY (txn_id) REFERENCES TransactionRecord(txn_id)
            )
            ''')
            
            # Review table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Review (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                reviewer_id INTEGER NOT NULL,
                reviewed_id INTEGER NOT NULL,
                txn_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reviewer_id) REFERENCES User(user_id),
                FOREIGN KEY (reviewed_id) REFERENCES User(user_id),
                FOREIGN KEY (txn_id) REFERENCES TransactionRecord(txn_id)
            )
            ''')
            
            # ItemImage table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ItemImage (
                image_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                image_path VARCHAR(255) NOT NULL,
                is_primary BOOLEAN DEFAULT 0,
                FOREIGN KEY (item_id) REFERENCES Item(item_id)
            )
            ''')
            
            # Notification table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Notification (
                notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                type VARCHAR(50) NOT NULL,
                reference_id INTEGER,
                read_status BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES User(user_id)
            )
            ''')
            
            # Insert some default categories
            categories = [
                ('Books', 'Textbooks, notebooks and other reading materials'),
                ('School Supplies', 'Pens, pencils, rulers, calculators, etc.'),
                ('Uniforms', 'School uniforms and clothing'),
                ('Electronics', 'Laptops, tablets, calculators, etc.'),
                ('Sports Equipment', 'Sports gear and equipment'),
                ('Musical Instruments', 'Instruments and accessories'),
                ('Art Supplies', 'Painting, drawing, craft materials')
            ]
            
            # Check if categories exist before inserting
            cursor.execute("SELECT COUNT(*) FROM Category")
            if cursor.fetchone()[0] == 0:
                for cat_name, cat_desc in categories:
                    cursor.execute(
                        "INSERT INTO Category (name, description) VALUES (?, ?)",
                        (cat_name, cat_desc)
                    )
            
            # Commit the changes
            self.conn.commit()
            print("Database setup completed successfully")
            
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
            if self.conn:
                self.conn.rollback()
    
    def close_connection(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
    
    def add_default_admin(self, username="admin", password="admin123", email="admin@school.edu"):
        """Add a default admin user if no admin exists"""
        import bcrypt
        
        cursor = self.conn.cursor()
        
        # Check if admin user exists
        cursor.execute("SELECT COUNT(*) FROM User WHERE role = 'admin'")
        if cursor.fetchone()[0] == 0:
            # Hash the password
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Insert admin user
            cursor.execute(
                "INSERT INTO User (username, password, email, full_name, role) VALUES (?, ?, ?, ?, ?)",
                (username, hashed.decode('utf-8'), email, "System Administrator", "admin")
            )
            self.conn.commit()
            print("Default admin user created")
        
if __name__ == "__main__":
    # Test database creation
    db_manager = DatabaseManager()
    db_manager.add_default_admin()
    db_manager.close_connection()
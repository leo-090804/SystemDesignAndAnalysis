"""
School Item Exchange/Donation Application
Main Application Entry Point
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database and views
from src.database.schema import DatabaseManager
from src.views.login_view import LoginView
from src.views.main_window import MainWindow

class SchoolExchangeApp:
    def __init__(self):
        """Initialize the application"""
        # Set up application style
        self.app = QApplication(sys.argv)
        self.app.setStyle('Fusion')
        
        # Set application font
        font = QFont("Segoe UI", 10)
        self.app.setFont(font)
        
        # Set application name and organization
        self.app.setApplicationName("School Exchange App")
        self.app.setOrganizationName("School")
        
        # Initialize database
        self.db_manager = DatabaseManager()
        self.db_connection = self.db_manager.conn
        
        # Initialize default admin user
        self.db_manager.add_default_admin()
        
        # Set up session data
        self.session = {
            'user_id': None,
            'username': None,
            'full_name': None,
            'role': None,
            'is_authenticated': False
        }
        
        # Start with login screen
        self.show_login()
    
    def show_login(self):
        """Show login screen"""
        self.login_view = LoginView(self.db_connection, self.login_successful)
        self.login_view.show()
    
    def login_successful(self, user_data):
        """Handle successful login"""
        # Save user data to session
        self.session['user_id'] = user_data['user_id']
        self.session['username'] = user_data['username']
        self.session['full_name'] = user_data['full_name']
        self.session['role'] = user_data['role']
        self.session['is_authenticated'] = True
        
        # Close login window and show main window
        self.login_view.close()
        self.main_window = MainWindow(self.db_connection, self.session, self.logout)
        self.main_window.show()
    
    def logout(self):
        """Handle logout"""
        # Clear session data
        self.session = {
            'user_id': None,
            'username': None,
            'full_name': None,
            'role': None,
            'is_authenticated': False
        }
        
        # Close main window and show login
        self.main_window.close()
        self.show_login()
    
    def run(self):
        """Run the application"""
        return self.app.exec_()

def main():
    """Application entry point"""
    # Create and run application
    app = SchoolExchangeApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()
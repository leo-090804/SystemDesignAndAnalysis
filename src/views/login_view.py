"""
Login view for the School Item Exchange/Donation Application
"""

import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QFormLayout, QTabWidget
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models.user import User

class LoginView(QWidget):
    def __init__(self, db_connection, login_callback):
        super().__init__()
        
        self.db_connection = db_connection
        self.user_model = User(db_connection)
        self.login_callback = login_callback
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        # Set window properties
        self.setWindowTitle('School Exchange - Login')
        self.setFixedSize(400, 450)
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)
        
        # App logo and title
        logo_layout = QHBoxLayout()
        
        # Logo placeholder (can be replaced with actual logo)
        logo_label = QLabel()
        logo_label.setFixedSize(64, 64)
        # logo_label.setPixmap(QPixmap('path/to/logo.png').scaled(64, 64, Qt.KeepAspectRatio))
        logo_layout.addWidget(logo_label)
        
        # App title
        title_label = QLabel('School Item Exchange')
        title_label.setFont(QFont('Segoe UI', 18, QFont.Bold))
        logo_layout.addWidget(title_label)
        logo_layout.addStretch()
        
        main_layout.addLayout(logo_layout)
        
        # Description
        description = QLabel('Login to access the school exchange platform for buying, selling, donating, and exchanging items within your school community.')
        description.setWordWrap(True)
        main_layout.addWidget(description)
        
        # Tab widget for login and register
        self.tab_widget = QTabWidget()
        
        # Login tab
        login_tab = QWidget()
        login_layout = QVBoxLayout()
        
        login_form = QFormLayout()
        
        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText('Enter your username')
        login_form.addRow('Username:', self.login_username)
        
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText('Enter your password')
        self.login_password.setEchoMode(QLineEdit.Password)
        login_form.addRow('Password:', self.login_password)
        
        login_layout.addLayout(login_form)
        
        # Login button
        self.login_button = QPushButton('Login')
        self.login_button.setMinimumHeight(40)
        self.login_button.clicked.connect(self.login)
        login_layout.addWidget(self.login_button)
        
        # Forgot password link
        forgot_password = QPushButton('Forgot password?')
        forgot_password.setFlat(True)
        forgot_password.setStyleSheet('text-align: left; text-decoration: underline; color: blue;')
        forgot_password.clicked.connect(self.forgot_password)
        login_layout.addWidget(forgot_password)
        
        login_tab.setLayout(login_layout)
        
        # Register tab
        register_tab = QWidget()
        register_layout = QVBoxLayout()
        
        register_form = QFormLayout()
        
        self.register_username = QLineEdit()
        self.register_username.setPlaceholderText('Choose a username')
        register_form.addRow('Username:', self.register_username)
        
        self.register_password = QLineEdit()
        self.register_password.setPlaceholderText('Choose a password')
        self.register_password.setEchoMode(QLineEdit.Password)
        register_form.addRow('Password:', self.register_password)
        
        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText('Confirm your password')
        self.confirm_password.setEchoMode(QLineEdit.Password)
        register_form.addRow('Confirm Password:', self.confirm_password)
        
        self.register_email = QLineEdit()
        self.register_email.setPlaceholderText('Enter your email')
        register_form.addRow('Email:', self.register_email)
        
        self.register_full_name = QLineEdit()
        self.register_full_name.setPlaceholderText('Enter your full name')
        register_form.addRow('Full Name:', self.register_full_name)
        
        self.register_school_id = QLineEdit()
        self.register_school_id.setPlaceholderText('Enter your school ID')
        register_form.addRow('School ID:', self.register_school_id)
        
        register_layout.addLayout(register_form)
        
        # Register button
        self.register_button = QPushButton('Register')
        self.register_button.setMinimumHeight(40)
        self.register_button.clicked.connect(self.register)
        register_layout.addWidget(self.register_button)
        
        register_tab.setLayout(register_layout)
        
        # Add tabs to widget
        self.tab_widget.addTab(login_tab, 'Login')
        self.tab_widget.addTab(register_tab, 'Register')
        
        main_layout.addWidget(self.tab_widget)
        
        # Footer text
        footer = QLabel('© 2025 School Exchange Application | All rights reserved')
        footer.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer)
        
        self.setLayout(main_layout)
    
    def login(self):
        """Handle login process"""
        username = self.login_username.text().strip()
        password = self.login_password.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, 'Error', 'Please enter both username and password.')
            return
        
        # Authenticate user
        success, message, user_data = self.user_model.authenticate(username, password)
        
        if success:
            # Get full user data
            user_info = self.user_model.get_user_by_id(user_data['user_id'])
            if user_info:
                user_data['username'] = user_info['username']
                user_data['email'] = user_info['email']
                user_data['full_name'] = user_info['full_name']
                
                self.login_callback(user_data)
            else:
                QMessageBox.critical(self, 'Error', 'Failed to retrieve user information.')
        else:
            QMessageBox.warning(self, 'Login Failed', message)
    
    def register(self):
        """Handle registration process"""
        username = self.register_username.text().strip()
        password = self.register_password.text().strip()
        confirm_password = self.confirm_password.text().strip()
        email = self.register_email.text().strip()
        full_name = self.register_full_name.text().strip()
        school_id = self.register_school_id.text().strip()
        
        # Validate inputs
        if not username or not password or not email or not full_name:
            QMessageBox.warning(self, 'Error', 'Please fill in all required fields.')
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, 'Error', 'Passwords do not match.')
            return
        
        # Create new user (default role is student)
        success, message = self.user_model.create_user(
            username, password, email, full_name, 'student', school_id
        )
        
        if success:
            QMessageBox.information(self, 'Registration Successful', 
                                   'Your account has been created. You can now login.')
            
            # Clear fields and switch to login tab
            self.register_username.clear()
            self.register_password.clear()
            self.confirm_password.clear()
            self.register_email.clear()
            self.register_full_name.clear()
            self.register_school_id.clear()
            
            self.tab_widget.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, 'Registration Failed', message)
    
    def forgot_password(self):
        """Handle forgot password request"""
        QMessageBox.information(self, 'Password Recovery',
                                'Please contact your school administrator to reset your password.')
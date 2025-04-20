"""
Main window for the School Item Exchange/Donation Application
"""

import sys
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QAction, QStatusBar, QMessageBox, QFrame
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.views.dashboard_view import DashboardView
from src.views.items_view import ItemsView
from src.views.events_view import EventsView
from src.views.transactions_view import TransactionsView
from src.views.item_approval_view import ItemApprovalView
from src.models.user import User

class MainWindow(QMainWindow):
    """Main window of the application"""
    def __init__(self, db_connection, session, logout_callback):
        super().__init__()
        self.db_connection = db_connection
        self.session = session
        self.logout_callback = logout_callback
        self.user_model = User(db_connection)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        # Set window properties
        self.setWindowTitle('School Item Exchange')
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)
        
        # Set up central widget and main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add sidebar menu (left side)
        self.setup_sidebar(main_layout)
        
        # Add content area (right side)
        content_container = QFrame()
        self.content_layout = QVBoxLayout(content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(content_container, 1)
        
        # Initialize the views
        self.dashboard_view = DashboardView(self.db_connection, self.session)
        self.items_view = ItemsView(self.db_connection, self.session)
        self.events_view = EventsView(self.db_connection, self.session)
        self.transactions_view = TransactionsView(self.db_connection, self.session)
        
        # Connect signals
        self.dashboard_view.change_view_requested.connect(self.change_view)
        
        # Set the dashboard view initially
        self.set_current_view(self.dashboard_view)
        
        # Setup menubar and status bar
        self.setup_menu()
        self.setup_statusbar()
        
        # Set central widget
        self.setCentralWidget(central_widget)
    
    def setup_sidebar(self, main_layout):
        """Set up the sidebar menu"""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setStyleSheet("""
            #sidebar {
                background-color: #34495e;
                min-width: 220px;
                max-width: 220px;
            }
            QPushButton {
                border: none;
                border-radius: 0;
                text-align: left;
                padding: 12px 20px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
            QPushButton:checked {
                background-color: #2980b9;
                font-weight: bold;
            }
            QLabel {
                color: white;
                padding: 20px;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(0)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        # App title
        title = QLabel('School Exchange')
        sidebar_layout.addWidget(title)
        
        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #2c3e50;")
        sidebar_layout.addWidget(separator)
        
        # Navigation buttons
        self.nav_buttons = []
        
        # Dashboard button
        dashboard_btn = QPushButton('Dashboard')
        dashboard_btn.setCheckable(True)
        dashboard_btn.setChecked(True)
        dashboard_btn.clicked.connect(lambda: self.change_view(0))
        sidebar_layout.addWidget(dashboard_btn)
        self.nav_buttons.append(dashboard_btn)
        
        # Items button
        items_btn = QPushButton('Items')
        items_btn.setCheckable(True)
        items_btn.clicked.connect(lambda: self.change_view(1))
        sidebar_layout.addWidget(items_btn)
        self.nav_buttons.append(items_btn)
        
        # Events button
        events_btn = QPushButton('Events')
        events_btn.setCheckable(True)
        events_btn.clicked.connect(lambda: self.change_view(2))
        sidebar_layout.addWidget(events_btn)
        self.nav_buttons.append(events_btn)
        
        # Transactions button
        transactions_btn = QPushButton('Transactions')
        transactions_btn.setCheckable(True)
        transactions_btn.clicked.connect(lambda: self.change_view(3))
        sidebar_layout.addWidget(transactions_btn)
        self.nav_buttons.append(transactions_btn)
        
        # Add moderator/admin specific menu items
        if self.session['role'] in ['moderator', 'admin']:
            # Add separator
            separator2 = QFrame()
            separator2.setFrameShape(QFrame.HLine)
            separator2.setFrameShadow(QFrame.Sunken)
            separator2.setStyleSheet("background-color: #2c3e50;")
            sidebar_layout.addWidget(separator2)
            
            # Item approval button
            item_approval_btn = QPushButton('Item Approvals')
            item_approval_btn.setCheckable(True)
            item_approval_btn.clicked.connect(self.show_item_approvals)
            sidebar_layout.addWidget(item_approval_btn)
            self.nav_buttons.append(item_approval_btn)
            
            if self.session['role'] == 'admin':
                # User management button
                user_mgmt_btn = QPushButton('User Management')
                user_mgmt_btn.setCheckable(True)
                user_mgmt_btn.clicked.connect(self.show_user_management)
                sidebar_layout.addWidget(user_mgmt_btn)
                self.nav_buttons.append(user_mgmt_btn)
                
                # System reports button
                reports_btn = QPushButton('System Reports')
                reports_btn.setCheckable(True)
                reports_btn.clicked.connect(self.show_system_reports)
                sidebar_layout.addWidget(reports_btn)
                self.nav_buttons.append(reports_btn)
        
        # Add user profile section at bottom
        sidebar_layout.addStretch()
        
        # User info
        user_frame = QFrame()
        user_frame.setStyleSheet("background-color: #2c3e50; padding: 10px;")
        user_layout = QVBoxLayout(user_frame)
        
        user_name = QLabel(self.session['full_name'])
        user_name.setStyleSheet("padding: 0px; font-size: 14px;")
        user_layout.addWidget(user_name)
        
        role_label = QLabel(f"Role: {self.session['role'].capitalize()}")
        role_label.setStyleSheet("padding: 0px; color: #bdc3c7; font-size: 12px;")
        user_layout.addWidget(role_label)
        
        # Logout button
        logout_btn = QPushButton('Logout')
        logout_btn.clicked.connect(self.logout)
        logout_btn.setStyleSheet("color: #e74c3c;")
        user_layout.addWidget(logout_btn)
        
        sidebar_layout.addWidget(user_frame)
        
        # Add sidebar to main layout
        main_layout.addWidget(sidebar)
    
    def setup_menu(self):
        """Set up the application menu bar"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu('File')
        
        # Export data action
        export_action = QAction('Export Data', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        # Separator
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Alt+F4')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menu_bar.addMenu('Help')
        
        # About action
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_statusbar(self):
        """Set up the status bar"""
        status_bar = QStatusBar()
        status_bar.showMessage(f'Logged in as {self.session["username"]} | Server: Local')
        self.setStatusBar(status_bar)
    
    def change_view(self, view_index):
        """Change the current view based on index"""
        # Update button states
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == view_index)
        
        # Set the appropriate view
        if view_index == 0:
            self.set_current_view(self.dashboard_view)
        elif view_index == 1:
            self.set_current_view(self.items_view)
        elif view_index == 2:
            self.set_current_view(self.events_view)
        elif view_index == 3:
            self.set_current_view(self.transactions_view)
    
    def set_current_view(self, view):
        """Set the current content view"""
        # Clear current content
        for i in reversed(range(self.content_layout.count())): 
            widget = self.content_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        
        # Add new view
        self.content_layout.addWidget(view)
    
    def show_item_approvals(self):
        """Show item approvals screen for moderators/admins"""
        # Update button states
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(btn.text() == 'Item Approvals')
            
        # Create and show the item approval view
        if not hasattr(self, 'item_approval_view'):
            self.item_approval_view = ItemApprovalView(self.db_connection, self.session)
        
        self.set_current_view(self.item_approval_view)
    
    def show_user_management(self):
        """Show user management screen for admins"""
        QMessageBox.information(self, "Coming Soon", 
                               "User management view will be implemented in the next version.")
    
    def show_system_reports(self):
        """Show system reports screen for admins"""
        QMessageBox.information(self, "Coming Soon", 
                               "System reports view will be implemented in the next version.")
    
    def export_data(self):
        """Export data to CSV/Excel"""
        QMessageBox.information(self, "Coming Soon", 
                               "Data export functionality will be implemented in the next version.")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About School Exchange App", 
                         "School Exchange & Donation Application\n\n"
                         "Version 1.0.0\n\n"
                         "© 2025 School Exchange System\n\n"
                         "A platform for students and teachers to buy, sell,\n"
                         "exchange and donate school items, and participate\n"
                         "in fundraising events.")
    
    def logout(self):
        """Handle logout action"""
        reply = QMessageBox.question(self, 'Confirm Logout', 
                                   'Are you sure you want to logout?',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.logout_callback()
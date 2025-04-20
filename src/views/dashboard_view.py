"""
Dashboard view for the School Item Exchange/Donation Application
"""

import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models.item import Item
from src.models.event import Event
from src.models.transaction import Transaction
from src.models.user import User

class StatCard(QFrame):
    """Widget for displaying a statistic with icon, title, and value"""
    def __init__(self, title, value, icon=None, color="#3498db"):
        super().__init__()
        self.setObjectName("statCard")
        self.setStyleSheet(f"""
            #statCard {{
                background-color: white;
                border-radius: 8px;
                border-left: 5px solid {color};
                padding: 10px;
            }}
            QLabel[objectName="valueLabel"] {{
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }}
            QLabel[objectName="titleLabel"] {{
                color: #7f8c8d;
                font-size: 14px;
            }}
        """)
        
        # Shadow effect
        self.setGraphicsEffect(None)
        
        layout = QHBoxLayout(self)
        
        # Icon (if provided)
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(QPixmap(icon).scaled(32, 32, Qt.KeepAspectRatio))
            layout.addWidget(icon_label)
        
        # Text content
        text_layout = QVBoxLayout()
        
        value_label = QLabel(str(value))
        value_label.setObjectName("valueLabel")
        text_layout.addWidget(value_label)
        
        title_label = QLabel(title)
        title_label.setObjectName("titleLabel")
        text_layout.addWidget(title_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()

class ActivityItem(QFrame):
    """Widget for displaying a single activity/notification item"""
    def __init__(self, title, description, time, icon=None, action=None):
        super().__init__()
        self.setObjectName("activityItem")
        self.setStyleSheet("""
            #activityItem {
                background-color: white;
                border-radius: 8px;
                margin-bottom: 5px;
                padding: 10px;
            }
            #activityItem:hover {
                background-color: #f5f5f5;
            }
            QLabel[objectName="timeLabel"] {
                color: #7f8c8d;
                font-size: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title and time in header layout
        header_layout = QHBoxLayout()
        
        # Icon (if provided)
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(QPixmap(icon).scaled(24, 24, Qt.KeepAspectRatio))
            header_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        header_layout.addWidget(title_label)
        
        # Stretch to push time to right
        header_layout.addStretch()
        
        # Time
        time_label = QLabel(time)
        time_label.setObjectName("timeLabel")
        header_layout.addWidget(time_label)
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Action button if provided
        if action:
            action_btn = QPushButton(action["text"])
            action_btn.clicked.connect(action["callback"])
            action_btn.setMaximumWidth(120)
            
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(action_btn)
            
            layout.addLayout(button_layout)

class DashboardView(QWidget):
    """Dashboard view showing summary statistics and recent activity"""
    
    # Signal to request view change
    change_view_requested = pyqtSignal(int)
    
    def __init__(self, db_connection, session):
        super().__init__()
        self.db_connection = db_connection
        self.session = session
        
        # Initialize models
        self.item_model = Item(db_connection)
        self.event_model = Event(db_connection)
        self.transaction_model = Transaction(db_connection)
        self.user_model = User(db_connection)
        
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Welcome message
        welcome_label = QLabel(f"Welcome back, {self.session['full_name']}!")
        welcome_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        main_layout.addWidget(welcome_label)
        
        # Stats section
        stats_label = QLabel("Overview")
        stats_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        main_layout.addWidget(stats_label)
        
        # Stats cards in a grid
        stats_grid = QGridLayout()
        stats_grid.setSpacing(15)
        
        # Placeholder stats (will be updated with real data)
        self.stats_cards = {
            'items': StatCard("Your Active Items", "0", color="#3498db"),
            'events': StatCard("Active Events", "0", color="#2ecc71"),
            'transactions': StatCard("Transactions", "0", color="#e74c3c"),
            'contributions': StatCard("Contributions", "0", color="#f39c12")
        }
        
        stats_grid.addWidget(self.stats_cards['items'], 0, 0)
        stats_grid.addWidget(self.stats_cards['events'], 0, 1)
        stats_grid.addWidget(self.stats_cards['transactions'], 1, 0)
        stats_grid.addWidget(self.stats_cards['contributions'], 1, 1)
        
        main_layout.addLayout(stats_grid)
        
        # Quick actions section
        actions_label = QLabel("Quick Actions")
        actions_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        main_layout.addWidget(actions_label)
        
        # Quick action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        list_item_btn = QPushButton("List New Item")
        list_item_btn.clicked.connect(lambda: self.change_view_requested.emit(1))  # Go to Items view
        actions_layout.addWidget(list_item_btn)
        
        browse_items_btn = QPushButton("Browse Items")
        browse_items_btn.clicked.connect(lambda: self.change_view_requested.emit(1))
        actions_layout.addWidget(browse_items_btn)
        
        view_events_btn = QPushButton("View Events")
        view_events_btn.clicked.connect(lambda: self.change_view_requested.emit(2))  # Go to Events view
        actions_layout.addWidget(view_events_btn)
        
        # If user is teacher or admin, add create event button
        if self.session['role'] in ['teacher', 'admin', 'moderator']:
            create_event_btn = QPushButton("Create Event")
            create_event_btn.clicked.connect(lambda: self.change_view_requested.emit(2))
            actions_layout.addWidget(create_event_btn)
        
        main_layout.addLayout(actions_layout)
        
        # Recent activity section
        activity_label = QLabel("Recent Activity")
        activity_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        main_layout.addWidget(activity_label)
        
        # Activity list in a scroll area
        activity_scroll = QScrollArea()
        activity_scroll.setWidgetResizable(True)
        activity_scroll.setFrameShape(QFrame.NoFrame)
        
        activity_container = QWidget()
        self.activity_layout = QVBoxLayout(activity_container)
        self.activity_layout.setContentsMargins(0, 0, 0, 0)
        self.activity_layout.setSpacing(10)
        
        # Placeholder for activity items (will be filled with data)
        self.activity_layout.addWidget(QLabel("Loading recent activity..."))
        
        activity_scroll.setWidget(activity_container)
        main_layout.addWidget(activity_scroll)
        
        # Set layout
        self.setLayout(main_layout)
    
    def load_data(self):
        """Load data from the database and update UI"""
        try:
            # Get user's active items count
            user_items = self.item_model.get_items(filters={
                'user_id': self.session['user_id'], 
                'status': 'approved'
            })
            self.stats_cards['items'].findChild(QLabel, "valueLabel").setText(str(len(user_items)))
            
            # Get active events count
            active_events = self.event_model.get_events(filters={'active_only': True})
            self.stats_cards['events'].findChild(QLabel, "valueLabel").setText(str(len(active_events)))
            
            # Get user's transaction count
            user_transactions = self.transaction_model.get_user_transactions(
                user_id=self.session['user_id']
            )
            self.stats_cards['transactions'].findChild(QLabel, "valueLabel").setText(str(len(user_transactions)))
            
            # Get user's contributions to events
            user_contributions = self.item_model.get_items(filters={
                'user_id': self.session['user_id'], 
                'event_id': 'NOT NULL'
            })
            self.stats_cards['contributions'].findChild(QLabel, "valueLabel").setText(str(len(user_contributions)))
            
            # Clear and reload activity items
            for i in reversed(range(self.activity_layout.count())): 
                self.activity_layout.itemAt(i).widget().setParent(None)
            
            # Add sample activities (in a real app, these would come from the database)
            # For this demo, we'll use some fake activities based on the user's data
            
            # Add recent items
            for item in user_items[:2]:  # Show only most recent 2
                self.activity_layout.addWidget(ActivityItem(
                    title=f"Your item: {item['title']}",
                    description=f"Category: {item['category']} | Condition: {item['condition']}",
                    time="Recently",
                    action={
                        "text": "View Item",
                        "callback": lambda: self.change_view_requested.emit(1)
                    }
                ))
            
            # Add recent events
            for event in active_events[:2]:  # Show only most recent 2
                self.activity_layout.addWidget(ActivityItem(
                    title=f"Event: {event['title']}",
                    description=f"From {event['start_date']} to {event['end_date']}",
                    time="Active event",
                    action={
                        "text": "View Event",
                        "callback": lambda: self.change_view_requested.emit(2)
                    }
                ))
            
            # Add recent transactions
            for txn in user_transactions[:3]:  # Show only most recent 3
                role = "seller" if txn['seller_id'] == self.session['user_id'] else "buyer"
                other_party = txn['buyer_username'] if role == "seller" else txn['seller_username']
                
                self.activity_layout.addWidget(ActivityItem(
                    title=f"Transaction: {txn['type']} - {txn['status']}",
                    description=f"Item: {txn['item_title']} | With: {other_party}",
                    time=txn['created_at'],
                    action={
                        "text": "View Details",
                        "callback": lambda: self.change_view_requested.emit(3)
                    }
                ))
            
            # If no activities, show a message
            if self.activity_layout.count() == 0:
                self.activity_layout.addWidget(QLabel("No recent activity"))
            
        except Exception as e:
            print(f"Error loading dashboard data: {str(e)}")
            # Add error message to activity section
            for i in reversed(range(self.activity_layout.count())): 
                self.activity_layout.itemAt(i).widget().setParent(None)
            self.activity_layout.addWidget(QLabel("Error loading activity data"))
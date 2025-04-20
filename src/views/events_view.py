"""
Events view for the School Item Exchange/Donation Application
"""

import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QFormLayout,
    QTextEdit, QDialog, QFileDialog, QMessageBox, QHeaderView, QDoubleSpinBox, QScrollArea, QFrame, QDateEdit, QProgressBar, QInputDialog
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal, QDate

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models.event import Event
from src.models.item import Item
from src.models.transaction import Transaction

class EventCard(QFrame):
    """Card widget for displaying an event in grid view"""
    clicked = pyqtSignal(dict)
    
    def __init__(self, event_data):
        super().__init__()
        self.event_data = event_data
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        self.setObjectName("eventCard")
        self.setStyleSheet(f"""
            #eventCard {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid #ddd;
            }}
            #eventCard:hover {{
                border: 1px solid #3498db;
                background-color: #f9f9f9;
            }}
        """)
        self.setMinimumSize(300, 200)
        self.setMaximumSize(350, 250)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(self.event_data['title'])
        title_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # Status chip
        status_label = QLabel(self.event_data['status'].upper())
        status_colors = {
            'upcoming': '#3498db',
            'active': '#2ecc71',
            'completed': '#95a5a6',
            'cancelled': '#e74c3c'
        }
        status_color = status_colors.get(self.event_data['status'], '#95a5a6')
        status_label.setStyleSheet(f"""
            background-color: {status_color};
            color: white;
            border-radius: 10px;
            padding: 3px 8px;
        """)
        status_label.setMaximumWidth(100)
        status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_label)
        
        # Dates
        dates_label = QLabel(f"From {self.event_data['start_date']} to {self.event_data['end_date']}")
        dates_label.setFont(QFont("Segoe UI", 9))
        layout.addWidget(dates_label)
        
        # Description (truncated)
        description = self.event_data['description']
        if len(description) > 100:
            description = description[:100] + "..."
            
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #555;")
        layout.addWidget(desc_label)
        
        # Progress bar if there's a target
        if self.event_data.get('target') and self.event_data.get('contribution_value'):
            progress_layout = QVBoxLayout()
            
            # Progress info
            progress_info = QLabel(f"${self.event_data['contribution_value']} of ${self.event_data['target']}")
            progress_info.setAlignment(Qt.AlignRight)
            progress_layout.addWidget(progress_info)
            
            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(self.event_data['target'])
            progress_bar.setValue(self.event_data['contribution_value'])
            progress_layout.addWidget(progress_bar)
            
            layout.addLayout(progress_layout)
        
        # Handle mouse events
        self.mousePressEvent = self.on_click
    
    def on_click(self, event):
        """Handle click event"""
        self.clicked.emit(self.event_data)


class EventDetailDialog(QDialog):
    """Dialog for showing event details and contributing items"""
    contribution_made = pyqtSignal(int, int)  # Signal emitted when contribution made (event_id, item_id)
    
    def __init__(self, db_connection, session, event_data, parent=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.session = session
        self.event_data = event_data
        self.event_model = Event(db_connection)
        self.item_model = Item(db_connection)
        self.transaction_model = Transaction(db_connection)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        self.setWindowTitle("Event Details")
        self.setMinimumSize(700, 600)
        
        main_layout = QVBoxLayout()
        
        # Event title
        title_label = QLabel(self.event_data['title'])
        title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # Event details in horizontal layout
        details_layout = QHBoxLayout()
        
        # Left side - event details
        info_layout = QVBoxLayout()
        
        # Status and dates
        status_date_layout = QHBoxLayout()
        
        status_label = QLabel(self.event_data['status'].upper())
        status_colors = {
            'upcoming': '#3498db',
            'active': '#2ecc71',
            'completed': '#95a5a6',
            'cancelled': '#e74c3c'
        }
        status_color = status_colors.get(self.event_data['status'], '#95a5a6')
        status_label.setStyleSheet(f"""
            background-color: {status_color};
            color: white;
            border-radius: 10px;
            padding: 5px 10px;
        """)
        status_label.setAlignment(Qt.AlignCenter)
        status_date_layout.addWidget(status_label)
        
        status_date_layout.addStretch()
        
        dates_label = QLabel(f"From {self.event_data['start_date']} to {self.event_data['end_date']}")
        dates_label.setFont(QFont("Segoe UI", 10))
        status_date_layout.addWidget(dates_label)
        
        info_layout.addLayout(status_date_layout)
        
        # Organizer info
        organizer_label = QLabel(f"Organized by: {self.event_data['organizer_full_name']}")
        info_layout.addWidget(organizer_label)
        
        # Description
        info_layout.addWidget(QLabel("Description:"))
        description = QTextEdit(self.event_data['description'])
        description.setReadOnly(True)
        description.setMinimumHeight(80)
        info_layout.addWidget(description)
        
        # Target and progress if applicable
        if self.event_data.get('target') and self.event_data['target'] > 0:
            target_layout = QVBoxLayout()
            
            # Target label
            target_header = QLabel(f"Target: ${self.event_data['target']}")
            target_header.setFont(QFont("Segoe UI", 10, QFont.Bold))
            target_layout.addWidget(target_header)
            
            # Progress info
            progress_info_layout = QHBoxLayout()
            
            raised_label = QLabel(f"Raised: ${self.event_data['contribution_value']}")
            progress_info_layout.addWidget(raised_label)
            
            progress_info_layout.addStretch()
            
            if self.event_data.get('progress_percentage'):
                percentage = round(self.event_data['progress_percentage'])
                percent_label = QLabel(f"{percentage}% Complete")
                progress_info_layout.addWidget(percent_label)
            
            target_layout.addLayout(progress_info_layout)
            
            # Progress bar
            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(self.event_data['target'])
            progress_bar.setValue(self.event_data['contribution_value'])
            target_layout.addWidget(progress_bar)
            
            info_layout.addLayout(target_layout)
        
        details_layout.addLayout(info_layout)
        
        main_layout.addLayout(details_layout)
        
        # Contributions section
        main_layout.addWidget(QLabel("Contributions:"))
        
        contributions_table = QTableWidget()
        contributions_table.setColumnCount(5)
        contributions_table.setHorizontalHeaderLabels([
            "Item", "Category", "Value", "Contributor", "Date"
        ])
        contributions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        contributions_table.verticalHeader().setVisible(False)
        
        # Load contributions
        self.load_contributions(contributions_table)
        
        main_layout.addWidget(contributions_table)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        # Only show contribute button if event is active/upcoming and user is not organizer
        if self.event_data['status'] in ['active', 'upcoming'] and self.session['user_id'] != self.event_data['organizer_id']:
            contribute_button = QPushButton("Contribute Item")
            contribute_button.clicked.connect(self.contribute_item)
            actions_layout.addWidget(contribute_button)
        
        # If user is organizer or admin, show edit/cancel buttons
        if (self.session['user_id'] == self.event_data['organizer_id'] or 
            self.session['role'] in ['admin', 'moderator']):
            
            if self.event_data['status'] in ['upcoming', 'active']:
                edit_button = QPushButton("Edit Event")
                edit_button.clicked.connect(self.edit_event)
                actions_layout.addWidget(edit_button)
                
                cancel_button = QPushButton("Cancel Event")
                cancel_button.clicked.connect(self.cancel_event)
                actions_layout.addWidget(cancel_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        actions_layout.addWidget(close_button)
        
        main_layout.addLayout(actions_layout)
        self.setLayout(main_layout)
    
    def load_contributions(self, table):
        """Load event contributions to the table"""
        try:
            contributions = self.event_model.get_event_contributions(self.event_data['event_id'])
            
            table.setRowCount(len(contributions))
            
            for row, contrib in enumerate(contributions):
                table.setItem(row, 0, QTableWidgetItem(contrib['title']))
                table.setItem(row, 1, QTableWidgetItem(contrib['category']))
                
                price_text = f"${contrib['price']}" if contrib['price'] else "N/A"
                table.setItem(row, 2, QTableWidgetItem(price_text))
                
                table.setItem(row, 3, QTableWidgetItem(contrib['contributor_full_name']))
                table.setItem(row, 4, QTableWidgetItem(contrib['created_at']))
        except Exception as e:
            print(f"Error loading contributions: {str(e)}")
    
    def contribute_item(self):
        """Handle contribute item action"""
        # Get user's available items
        user_items = self.item_model.get_items(filters={
            'user_id': self.session['user_id'], 
            'status': 'approved'
        })
        
        if not user_items:
            QMessageBox.information(self, "No Items Available", 
                                 "You don't have any approved items to contribute.\n"
                                 "Please create and list some items first.")
            return
        
        # Show item selection dialog
        selected_item = self.select_item_dialog(user_items)
        if not selected_item:
            return
        
        # Confirm contribution
        reply = QMessageBox.question(
            self, 'Confirm Contribution',
            f"Are you sure you want to contribute '{selected_item['title']}' to this event?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Create transaction for event contribution
            success, message, txn_id = self.transaction_model.create_transaction(
                item_id=selected_item['item_id'],
                buyer_id=self.event_data['organizer_id'],  # Event organizer is the receiver
                txn_type='event_contribution',
                event_id=self.event_data['event_id']
            )
            
            if success:
                QMessageBox.information(self, "Success", 
                                     "Your contribution has been recorded!\n"
                                     "Thank you for contributing to this event.")
                
                # Update event data
                updated_event = self.event_model.get_event_by_id(self.event_data['event_id'])
                if updated_event:
                    self.event_data = updated_event
                
                # Emit signal
                self.contribution_made.emit(self.event_data['event_id'], selected_item['item_id'])
                
                # Close dialog
                self.accept()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def select_item_dialog(self, items):
        """Show dialog to select an item to contribute"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Item to Contribute")
        dialog.setMinimumSize(400, 300)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Select an item to contribute to this event:"))
        
        # Item table
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Title", "Category", "Condition", "Value"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        
        table.setRowCount(len(items))
        
        for row, item in enumerate(items):
            table.setItem(row, 0, QTableWidgetItem(item['title']))
            table.setItem(row, 1, QTableWidgetItem(item['category']))
            table.setItem(row, 2, QTableWidgetItem(item['condition']))
            
            price_text = f"${item['price']}" if item['price'] else "N/A"
            table.setItem(row, 3, QTableWidgetItem(price_text))
        
        layout.addWidget(table)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        select_btn = QPushButton("Select")
        select_btn.setDefault(True)
        cancel_btn = QPushButton("Cancel")
        
        buttons_layout.addWidget(select_btn)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        
        dialog.setLayout(layout)
        
        # Selected item
        selected = [None]
        
        def on_select():
            rows = table.selectionModel().selectedRows()
            if rows:
                row = rows[0].row()
                selected[0] = items[row]
                dialog.accept()
        
        select_btn.clicked.connect(on_select)
        cancel_btn.clicked.connect(dialog.reject)
        table.doubleClicked.connect(on_select)
        
        # Show dialog
        result = dialog.exec_()
        
        if result == QDialog.Accepted and selected[0]:
            return selected[0]
        return None
    
    def edit_event(self):
        """Handle edit event action"""
        QMessageBox.information(self, "Edit Event", "This feature is coming soon.")
    
    def cancel_event(self):
        """Handle cancel event action"""
        # Ask for reason
        reason, ok = QInputDialog.getText(self, "Cancel Event", 
                                      "Please provide a reason for cancelling this event:")
        
        if not ok:
            return
        
        # Confirm cancellation
        reply = QMessageBox.question(
            self, 'Cancel Event',
            "Are you sure you want to cancel this event?\n"
            "This will notify all contributors and remove their items from the event.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.event_model.cancel_event(
                self.event_data['event_id'], 
                self.session['user_id'],
                reason
            )
            
            if success:
                QMessageBox.information(self, "Success", "Event has been cancelled.")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", message)


class NewEventDialog(QDialog):
    """Dialog for creating a new event"""
    
    def __init__(self, db_connection, session):
        super().__init__()
        self.db_connection = db_connection
        self.session = session
        self.event_model = Event(db_connection)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        self.setWindowTitle("Create New Event")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Form layout for event details
        form_layout = QFormLayout()
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter event title")
        form_layout.addRow("Title:", self.title_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Describe the purpose and goals of this event")
        self.description_input.setMinimumHeight(100)
        form_layout.addRow("Description:", self.description_input)
        
        # Target amount
        self.target_input = QDoubleSpinBox()
        self.target_input.setRange(0, 10000)
        self.target_input.setSingleStep(10)
        self.target_input.setValue(100)
        self.target_input.setPrefix("$")
        form_layout.addRow("Target Amount:", self.target_input)
        
        # Date range
        date_range_layout = QHBoxLayout()
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        date_range_layout.addWidget(self.start_date)
        
        date_range_layout.addWidget(QLabel("to"))
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate().addDays(14))  # Default to 2 weeks
        date_range_layout.addWidget(self.end_date)
        
        form_layout.addRow("Date Range:", date_range_layout)
        
        # Add image button (optional)
        image_layout = QHBoxLayout()
        self.image_path = None
        
        self.image_label = QLabel("No image selected")
        image_layout.addWidget(self.image_label)
        
        select_image_btn = QPushButton("Select Image")
        select_image_btn.clicked.connect(self.select_image)
        image_layout.addWidget(select_image_btn)
        
        form_layout.addRow("Event Image:", image_layout)
        
        layout.addLayout(form_layout)
        
        # Button box
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        
        create_btn = QPushButton("Create Event")
        create_btn.clicked.connect(self.create_event)
        create_btn.setDefault(True)
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def select_image(self):
        """Open file dialog to select an event image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Event Image", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            self.image_path = file_path
            self.image_label.setText(os.path.basename(file_path))
    
    def create_event(self):
        """Create new event with entered data"""
        # Validate inputs
        title = self.title_input.text().strip()
        description = self.description_input.toPlainText().strip()
        target = self.target_input.value()
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        if not title:
            QMessageBox.warning(self, "Validation Error", "Please enter an event title.")
            return
        
        if not description:
            QMessageBox.warning(self, "Validation Error", "Please enter an event description.")
            return
        
        if self.start_date.date() > self.end_date.date():
            QMessageBox.warning(self, "Validation Error", "End date must be after start date.")
            return
        
        # Create the event
        success, message, event_id = self.event_model.create_event(
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date,
            organizer_id=self.session['user_id'],
            target=target,
            image_path=self.image_path
        )
        
        if success:
            QMessageBox.information(self, "Success", "Event created successfully!")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", message)


class EventsView(QWidget):
    """Events view showing available events and user's events"""
    def __init__(self, db_connection, session):
        super().__init__()
        self.db_connection = db_connection
        self.session = session
        self.event_model = Event(db_connection)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        
        # Header with create event button (for teachers/admins/moderators)
        header_layout = QHBoxLayout()
        
        header_layout.addWidget(QLabel("School Events"))
        
        header_layout.addStretch()
        
        if self.session['role'] in ['teacher', 'admin', 'moderator']:
            create_event_btn = QPushButton("Create New Event")
            create_event_btn.clicked.connect(self.create_event)
            header_layout.addWidget(create_event_btn)
        
        main_layout.addLayout(header_layout)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.status_filter = QComboBox()
        self.status_filter.addItem("All Events", None)
        self.status_filter.addItem("Active", "active")
        self.status_filter.addItem("Upcoming", "upcoming")
        self.status_filter.addItem("Completed", "completed")
        self.status_filter.addItem("Cancelled", "cancelled")
        self.status_filter.currentIndexChanged.connect(self.load_events)
        filter_layout.addWidget(self.status_filter)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search events...")
        self.search_input.returnPressed.connect(self.load_events)
        filter_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.load_events)
        filter_layout.addWidget(search_btn)
        
        main_layout.addLayout(filter_layout)
        
        # Events display area - scrollable grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        self.events_container = QWidget()
        self.events_layout = QHBoxLayout(self.events_container)
        self.events_layout.setContentsMargins(0, 0, 0, 0)
        self.events_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.events_layout.setSpacing(15)
        
        scroll_area.setWidget(self.events_container)
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)
        
        # Load initial events
        self.load_events()
    
    def load_events(self):
        """Load events based on filters"""
        # Clear current events
        for i in reversed(range(self.events_layout.count())):
            self.events_layout.itemAt(i).widget().setParent(None)
        
        # Build filters
        filters = {}
        
        if self.status_filter.currentData():
            filters['status'] = self.status_filter.currentData()
        
        if self.search_input.text():
            filters['search'] = self.search_input.text()
        
        # Get events from database
        events = self.event_model.get_events(filters=filters, sort_by='start_date', order='DESC')
        
        # Add events to layout
        for event in events:
            event_card = EventCard(event)
            event_card.clicked.connect(self.show_event_details)
            self.events_layout.addWidget(event_card)
        
        # Add a "no events" message if no events found
        if not events:
            no_events = QLabel("No events found matching your search criteria.")
            no_events.setAlignment(Qt.AlignCenter)
            self.events_layout.addWidget(no_events)
    
    def show_event_details(self, event_data):
        """Show event details dialog"""
        # If we only have summary data, fetch full event data
        if not event_data.get('description'):
            full_event = self.event_model.get_event_by_id(event_data['event_id'])
            if full_event:
                event_data = full_event
            else:
                QMessageBox.warning(self, "Error", "Could not retrieve event details")
                return
        
        dialog = EventDetailDialog(self.db_connection, self.session, event_data)
        dialog.contribution_made.connect(self.handle_contribution_made)
        
        if dialog.exec_() == QDialog.Accepted:
            # Reload events in case anything changed
            self.load_events()
    
    def create_event(self):
        """Create a new event"""
        dialog = NewEventDialog(self.db_connection, self.session)
        if dialog.exec_() == QDialog.Accepted:
            self.load_events()
    
    def handle_contribution_made(self, event_id, item_id):
        """Handle contribution made signal"""
        # Reload events
        self.load_events()
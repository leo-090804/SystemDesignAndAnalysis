"""
Item approval view for School Item Exchange/Donation Application
Allows administrators and moderators to review and approve/reject pending items
"""

import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFormLayout, QTextEdit,
    QMessageBox, QFrame, QSplitter, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models.item import Item

class ItemApprovalView(QWidget):
    """View for managing item approvals"""
    
    def __init__(self, db_connection, session):
        super().__init__()
        self.db_connection = db_connection
        self.session = session
        self.item_model = Item(db_connection)
        
        self.current_item = None
        self.init_ui()
        self.load_pending_items()
    
    def init_ui(self):
        """Initialize the UI components"""
        main_layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Item Approval Dashboard")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_pending_items)
        header_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(header_layout)
        
        # Splitter for table and details
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Pending items table
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        
        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(5)
        self.pending_table.setHorizontalHeaderLabels(["ID", "Title", "Category", "Submitter", "Date"])
        self.pending_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.pending_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pending_table.setSelectionMode(QTableWidget.SingleSelection)
        self.pending_table.itemSelectionChanged.connect(self.item_selected)
        
        table_layout.addWidget(self.pending_table)
        
        # Right side - Item details
        details_container = QScrollArea()
        details_container.setWidgetResizable(True)
        details_frame = QWidget()
        self.details_layout = QVBoxLayout(details_frame)
        
        # No item selected initially
        self.no_selection_label = QLabel("Select an item from the list to view details")
        self.no_selection_label.setAlignment(Qt.AlignCenter)
        self.details_layout.addWidget(self.no_selection_label)
        
        # Item details container (hidden initially)
        self.item_details = QWidget()
        item_details_layout = QVBoxLayout(self.item_details)
        
        # Item title
        self.item_title = QLabel()
        self.item_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        item_details_layout.addWidget(self.item_title)
        
        # Item details in horizontal layout
        details_layout = QHBoxLayout()
        
        # Left side - image if available
        image_frame = QFrame()
        image_frame.setFixedSize(200, 200)
        image_frame.setFrameShape(QFrame.Box)
        image_frame.setLineWidth(1)
        
        image_layout = QVBoxLayout(image_frame)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText("No image available")
        
        image_layout.addWidget(self.image_label)
        details_layout.addWidget(image_frame)
        
        # Right side - item details
        info_layout = QVBoxLayout()
        
        # Item information in form layout
        form_layout = QFormLayout()
        
        self.category_label = QLabel()
        form_layout.addRow("Category:", self.category_label)
        
        self.condition_label = QLabel()
        form_layout.addRow("Condition:", self.condition_label)
        
        self.price_label = QLabel()
        form_layout.addRow("Price:", self.price_label)
        
        self.owner_label = QLabel()
        form_layout.addRow("Owner:", self.owner_label)
        
        self.date_label = QLabel()
        form_layout.addRow("Submitted:", self.date_label)
        
        info_layout.addLayout(form_layout)
        
        # Item description
        info_layout.addWidget(QLabel("Description:"))
        self.description_display = QTextEdit()
        self.description_display.setReadOnly(True)
        self.description_display.setMaximumHeight(100)
        info_layout.addWidget(self.description_display)
        
        # Exchange preferences if any
        info_layout.addWidget(QLabel("Exchange Preferences:"))
        self.exchange_display = QTextEdit()
        self.exchange_display.setReadOnly(True)
        self.exchange_display.setMaximumHeight(60)
        info_layout.addWidget(self.exchange_display)
        
        details_layout.addLayout(info_layout)
        item_details_layout.addLayout(details_layout)
        
        # Add rejection reason input
        item_details_layout.addWidget(QLabel("Rejection Reason (if applicable):"))
        self.rejection_reason = QTextEdit()
        self.rejection_reason.setMaximumHeight(60)
        self.rejection_reason.setPlaceholderText("Enter reason if rejecting the item...")
        item_details_layout.addWidget(self.rejection_reason)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.approve_btn = QPushButton("Approve Item")
        self.approve_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.approve_btn.clicked.connect(self.approve_item)
        actions_layout.addWidget(self.approve_btn)
        
        self.reject_btn = QPushButton("Reject Item")
        self.reject_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.reject_btn.clicked.connect(self.reject_item)
        actions_layout.addWidget(self.reject_btn)
        
        item_details_layout.addLayout(actions_layout)
        
        # Hide details initially
        self.item_details.hide()
        
        # Add all to details layout
        self.details_layout.addWidget(self.item_details)
        
        details_container.setWidget(details_frame)
        
        # Add widgets to splitter
        splitter.addWidget(table_container)
        splitter.addWidget(details_container)
        
        # Set splitter sizes
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
        # Add status section at the bottom
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.count_label = QLabel("0 items pending approval")
        status_layout.addWidget(self.count_label)
        
        main_layout.addLayout(status_layout)
    
    def load_pending_items(self):
        """Load pending items that need approval"""
        # Clear existing items
        self.pending_table.setRowCount(0)
        
        # Get pending items from database
        items = self.item_model.get_pending_items(limit=100)
        
        # Update count label
        self.count_label.setText(f"{len(items)} items pending approval")
        
        # Add items to table
        self.pending_table.setRowCount(len(items))
        
        for row, item in enumerate(items):
            self.pending_table.setItem(row, 0, QTableWidgetItem(str(item['item_id'])))
            self.pending_table.setItem(row, 1, QTableWidgetItem(item['title']))
            self.pending_table.setItem(row, 2, QTableWidgetItem(item['category']))
            self.pending_table.setItem(row, 3, QTableWidgetItem(item['owner_username']))
            self.pending_table.setItem(row, 4, QTableWidgetItem(item['created_at']))
        
        if len(items) > 0:
            self.status_label.setText("Select an item to review")
        else:
            self.status_label.setText("No items pending approval")
            self.item_details.hide()
            self.no_selection_label.show()
    
    def item_selected(self):
        """Handle item selection from the table"""
        selected_rows = self.pending_table.selectionModel().selectedRows()
        
        if not selected_rows:
            self.item_details.hide()
            self.no_selection_label.show()
            self.current_item = None
            return
        
        # Get item ID from first column
        row_index = selected_rows[0].row()
        item_id = int(self.pending_table.item(row_index, 0).text())
        
        # Fetch complete item details
        item_data = self.item_model.get_item_by_id(item_id)
        
        if not item_data:
            QMessageBox.warning(self, "Error", "Could not retrieve item details")
            return
        
        # Store current item
        self.current_item = item_data
        
        # Update UI with item details
        self.item_title.setText(item_data['title'])
        self.category_label.setText(item_data['category'])
        self.condition_label.setText(item_data['condition'])
        
        if item_data['price']:
            self.price_label.setText(f"${item_data['price']}")
        else:
            self.price_label.setText("Not for sale")
            
        self.owner_label.setText(f"{item_data['owner_full_name']} ({item_data['owner_username']})")
        self.date_label.setText(item_data['created_at'])
        
        self.description_display.setText(item_data['description'])
        
        if item_data['exchange_preferences']:
            self.exchange_display.setText(item_data['exchange_preferences'])
            self.exchange_display.show()
        else:
            self.exchange_display.setText("None specified")
        
        # Show image if available
        if item_data.get('images') and len(item_data['images']) > 0:
            primary_image = None
            for img in item_data['images']:
                if img['is_primary']:
                    primary_image = img['path']
                    break
            
            if primary_image and os.path.exists(primary_image):
                self.image_label.setPixmap(QPixmap(primary_image).scaled(180, 180, Qt.KeepAspectRatio))
            else:
                self.image_label.setText("Image not available")
        else:
            self.image_label.setText("No image available")
        
        # Reset rejection reason
        self.rejection_reason.clear()
        
        # Show details, hide no selection message
        self.no_selection_label.hide()
        self.item_details.show()
        
        # Update status
        self.status_label.setText(f"Reviewing item #{item_id}: {item_data['title']}")
    
    def approve_item(self):
        """Approve the selected item"""
        if not self.current_item:
            return
        
        # Confirm action
        reply = QMessageBox.question(
            self, 'Confirm Approval',
            f"Are you sure you want to approve the item '{self.current_item['title']}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Call model to approve item
        success, message = self.item_model.approve_item(
            item_id=self.current_item['item_id'],
            moderator_id=self.session['user_id']
        )
        
        if success:
            QMessageBox.information(self, "Success", "Item approved successfully!")
            # Refresh the pending items list
            self.load_pending_items()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def reject_item(self):
        """Reject the selected item"""
        if not self.current_item:
            return
        
        # Get rejection reason
        reason = self.rejection_reason.toPlainText().strip()
        if not reason:
            QMessageBox.warning(
                self, "Missing Information",
                "Please provide a reason for rejecting this item."
            )
            return
        
        # Confirm action
        reply = QMessageBox.question(
            self, 'Confirm Rejection',
            f"Are you sure you want to reject the item '{self.current_item['title']}'?\n\n"
            f"Reason: {reason}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Call model to reject item
        success, message = self.item_model.reject_item(
            item_id=self.current_item['item_id'],
            moderator_id=self.session['user_id'],
            reason=reason
        )
        
        if success:
            QMessageBox.information(self, "Success", "Item rejected successfully!")
            # Refresh the pending items list
            self.load_pending_items()
        else:
            QMessageBox.warning(self, "Error", message)
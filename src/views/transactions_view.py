"""
Transactions view for the School Item Exchange/Donation Application
"""

import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QTabWidget, QFormLayout,
    QTextEdit, QDialog, QMessageBox, QHeaderView, QFrame, QInputDialog
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, pyqtSignal

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models.transaction import Transaction
from src.models.item import Item

class TransactionDetailDialog(QDialog):
    """Dialog for showing transaction details"""
    status_updated = pyqtSignal(int, str)  # Signal emitted when transaction status is updated (transaction_id, new_status)
    
    def __init__(self, db_connection, session, transaction_data, parent=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.session = session
        self.transaction_data = transaction_data
        self.transaction_model = Transaction(db_connection)
        self.item_model = Item(db_connection)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        self.setWindowTitle("Transaction Details")
        self.setMinimumSize(500, 400)
        
        main_layout = QVBoxLayout()
        
        # Transaction ID and Type
        header_layout = QHBoxLayout()
        
        transaction_id_label = QLabel(f"Transaction #{self.transaction_data['txn_id']}")
        transaction_id_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_layout.addWidget(transaction_id_label)
        
        header_layout.addStretch()
        
        # Transaction type badge
        type_label = QLabel(self.get_transaction_type_display())
        type_colors = {
            'sale': '#3498db',
            'donation': '#2ecc71',
            'exchange': '#f39c12',
            'event_contribution': '#9b59b6'
        }
        type_color = type_colors.get(self.transaction_data['type'], '#95a5a6')
        type_label.setStyleSheet(f"""
            background-color: {type_color};
            color: white;
            border-radius: 10px;
            padding: 5px 10px;
        """)
        header_layout.addWidget(type_label)
        
        main_layout.addLayout(header_layout)
        
        # Transaction status
        status_layout = QHBoxLayout()
        
        status_layout.addWidget(QLabel("Status:"))
        
        status_label = QLabel(self.transaction_data['status'].upper())
        status_colors = {
            'pending': '#f39c12',
            'approved': '#2ecc71',
            'rejected': '#e74c3c',
            'completed': '#3498db',
            'cancelled': '#95a5a6'
        }
        status_color = status_colors.get(self.transaction_data['status'], '#95a5a6')
        status_label.setStyleSheet(f"""
            color: {status_color};
            font-weight: bold;
        """)
        status_layout.addWidget(status_label)
        
        status_layout.addStretch()
        
        # Date
        date_label = QLabel(f"Date: {self.transaction_data['created_at']}")
        status_layout.addWidget(date_label)
        
        main_layout.addLayout(status_layout)
        
        main_layout.addSpacing(10)
        
        # Item details
        item_frame = QFrame()
        item_frame.setFrameShape(QFrame.StyledPanel)
        item_frame.setStyleSheet("background-color: #f8f9fa; padding: 10px; border-radius: 5px;")
        
        item_layout = QVBoxLayout(item_frame)
        
        item_header = QLabel("Item Details")
        item_header.setFont(QFont("Segoe UI", 11, QFont.Bold))
        item_layout.addWidget(item_header)
        
        item_details_layout = QFormLayout()
        
        item_details_layout.addRow("Item Name:", QLabel(self.transaction_data['item_title']))
        item_details_layout.addRow("Category:", QLabel(self.transaction_data['item_category']))
        item_details_layout.addRow("Condition:", QLabel(self.transaction_data['item_condition']))
        
        price_text = f"${self.transaction_data['amount']}" if self.transaction_data['amount'] else "N/A"
        item_details_layout.addRow("Price:", QLabel(price_text))
        
        item_layout.addLayout(item_details_layout)
        
        main_layout.addWidget(item_frame)
        
        # Party details
        parties_layout = QHBoxLayout()
        
        # Seller/Owner
        seller_frame = QFrame()
        seller_frame.setFrameShape(QFrame.StyledPanel)
        seller_frame.setStyleSheet("background-color: #e8f4f8; padding: 10px; border-radius: 5px;")
        
        seller_layout = QVBoxLayout(seller_frame)
        
        seller_header = QLabel("Seller/Owner")
        seller_header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        seller_layout.addWidget(seller_header)
        
        seller_name = QLabel(self.transaction_data['seller_full_name'])
        seller_layout.addWidget(seller_name)
        
        seller_id_label = QLabel(f"ID: {self.transaction_data['seller_id']}")
        seller_id_label.setStyleSheet("color: #777;")
        seller_layout.addWidget(seller_id_label)
        
        parties_layout.addWidget(seller_frame)
        
        # Arrow between parties
        arrow_label = QLabel("→")
        arrow_label.setFont(QFont("Segoe UI", 20))
        arrow_label.setAlignment(Qt.AlignCenter)
        parties_layout.addWidget(arrow_label)
        
        # Buyer/Recipient
        buyer_frame = QFrame()
        buyer_frame.setFrameShape(QFrame.StyledPanel)
        buyer_frame.setStyleSheet("background-color: #e8f8ef; padding: 10px; border-radius: 5px;")
        
        buyer_layout = QVBoxLayout(buyer_frame)
        
        buyer_header = QLabel("Buyer/Recipient")
        buyer_header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        buyer_layout.addWidget(buyer_header)
        
        buyer_name = QLabel(self.transaction_data['buyer_full_name'])
        buyer_layout.addWidget(buyer_name)
        
        buyer_id_label = QLabel(f"ID: {self.transaction_data['buyer_id']}")
        buyer_id_label.setStyleSheet("color: #777;")
        buyer_layout.addWidget(buyer_id_label)
        
        parties_layout.addWidget(buyer_frame)
        
        main_layout.addLayout(parties_layout)
        
        # Notes if any
        if self.transaction_data.get('notes'):
            notes_label = QLabel("Notes:")
            notes_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            main_layout.addWidget(notes_label)
            
            notes_text = QTextEdit(self.transaction_data['notes'])
            notes_text.setReadOnly(True)
            notes_text.setMaximumHeight(80)
            main_layout.addWidget(notes_text)
        
        # Actions buttons based on role and status
        actions_layout = QHBoxLayout()
        
        # If pending transaction
        if self.transaction_data['status'] == 'pending':
            # If current user is the seller
            if self.session['user_id'] == self.transaction_data['seller_id']:
                # Allow approve/reject
                approve_btn = QPushButton("Approve")
                approve_btn.clicked.connect(self.approve_transaction)
                actions_layout.addWidget(approve_btn)
                
                reject_btn = QPushButton("Reject")
                reject_btn.clicked.connect(self.reject_transaction)
                actions_layout.addWidget(reject_btn)
            
            # If current user is buyer
            elif self.session['user_id'] == self.transaction_data['buyer_id']:
                # Allow cancel
                cancel_btn = QPushButton("Cancel Request")
                cancel_btn.clicked.connect(self.cancel_transaction)
                actions_layout.addWidget(cancel_btn)
        
        # If approved transaction
        elif self.transaction_data['status'] == 'approved':
            # If current user is the seller
            if self.session['user_id'] == self.transaction_data['seller_id']:
                # Allow marking complete
                complete_btn = QPushButton("Mark as Completed")
                complete_btn.clicked.connect(self.complete_transaction)
                actions_layout.addWidget(complete_btn)
                
                cancel_btn = QPushButton("Cancel")
                cancel_btn.clicked.connect(self.cancel_transaction)
                actions_layout.addWidget(cancel_btn)
            
            # If current user is buyer
            elif self.session['user_id'] == self.transaction_data['buyer_id']:
                # Allow cancel
                cancel_btn = QPushButton("Cancel")
                cancel_btn.clicked.connect(self.cancel_transaction)
                actions_layout.addWidget(cancel_btn)
        
        # Add close button
        actions_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        actions_layout.addWidget(close_btn)
        
        main_layout.addLayout(actions_layout)
        
        self.setLayout(main_layout)
    
    def get_transaction_type_display(self):
        """Get display name for transaction type"""
        type_map = {
            'sale': 'Sale',
            'donation': 'Donation',
            'exchange': 'Exchange',
            'event_contribution': 'Event Contribution'
        }
        return type_map.get(self.transaction_data['type'], 
                           self.transaction_data['type'].replace('_', ' ').title())
    
    def approve_transaction(self):
        """Handle approve transaction action"""
        reply = QMessageBox.question(
            self, 'Approve Transaction',
            "Are you sure you want to approve this transaction?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.transaction_model.update_transaction_status(
                transaction_id=self.transaction_data['txn_id'],
                user_id=self.session['user_id'],
                status='approved'
            )
            
            if success:
                QMessageBox.information(self, "Success", "Transaction has been approved.")
                self.transaction_data['status'] = 'approved'
                self.status_updated.emit(self.transaction_data['txn_id'], 'approved')
                self.accept()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def reject_transaction(self):
        """Handle reject transaction action"""
        reason, ok = QInputDialog.getText(
            self, 'Reject Transaction',
            'Please provide a reason for rejection:',
            QLineEdit.Normal, ""
        )
        
        if ok:
            success, message = self.transaction_model.update_transaction_status(
                transaction_id=self.transaction_data['transaction_id'],
                user_id=self.session['user_id'],
                status='rejected',
                notes=reason
            )
            
            if success:
                QMessageBox.information(self, "Success", "Transaction has been rejected.")
                self.transaction_data['status'] = 'rejected'
                self.status_updated.emit(self.transaction_data['transaction_id'], 'rejected')
                self.accept()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def complete_transaction(self):
        """Handle complete transaction action"""
        reply = QMessageBox.question(
            self, 'Complete Transaction',
            "Are you sure you want to mark this transaction as completed?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.transaction_model.update_transaction_status(
                transaction_id=self.transaction_data['transaction_id'],
                user_id=self.session['user_id'],
                status='completed'
            )
            
            if success:
                QMessageBox.information(self, "Success", "Transaction has been marked as completed.")
                self.transaction_data['status'] = 'completed'
                self.status_updated.emit(self.transaction_data['transaction_id'], 'completed')
                self.accept()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def cancel_transaction(self):
        """Handle cancel transaction action"""
        reason, ok = QInputDialog.getText(
            self, 'Cancel Transaction',
            'Please provide a reason for cancellation:',
            QLineEdit.Normal, ""
        )
        
        if ok:
            success, message = self.transaction_model.update_transaction_status(
                transaction_id=self.transaction_data['transaction_id'],
                user_id=self.session['user_id'],
                status='cancelled',
                notes=reason
            )
            
            if success:
                QMessageBox.information(self, "Success", "Transaction has been cancelled.")
                self.transaction_data['status'] = 'cancelled'
                self.status_updated.emit(self.transaction_data['transaction_id'], 'cancelled')
                self.accept()
            else:
                QMessageBox.warning(self, "Error", message)


class TransactionsView(QWidget):
    """Transactions view showing user's incoming and outgoing transactions"""
    def __init__(self, db_connection, session):
        super().__init__()
        self.db_connection = db_connection
        self.session = session
        self.transaction_model = Transaction(db_connection)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Tab widget for My Incoming/Outgoing Transactions
        self.tab_widget = QTabWidget()
        
        # Tab 1: Incoming Transactions
        self.incoming_tab = QWidget()
        self.setup_incoming_tab()
        self.tab_widget.addTab(self.incoming_tab, "Incoming Transactions")
        
        # Tab 2: Outgoing Transactions
        self.outgoing_tab = QWidget()
        self.setup_outgoing_tab()
        self.tab_widget.addTab(self.outgoing_tab, "Outgoing Transactions")
        
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
    
    def setup_incoming_tab(self):
        """Setup the incoming transactions tab"""
        layout = QVBoxLayout(self.incoming_tab)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.incoming_status_filter = QComboBox()
        self.incoming_status_filter.addItem("All Statuses", None)
        statuses = [("Pending", "pending"), ("Approved", "approved"), 
                   ("Completed", "completed"), ("Rejected", "rejected"),
                   ("Cancelled", "cancelled")]
        for label, value in statuses:
            self.incoming_status_filter.addItem(label, value)
        self.incoming_status_filter.currentIndexChanged.connect(self.load_incoming_transactions)
        filter_layout.addWidget(self.incoming_status_filter)
        
        self.incoming_type_filter = QComboBox()
        self.incoming_type_filter.addItem("All Types", None)
        types = [("Sales", "sale"), ("Donations", "donation"), 
               ("Exchanges", "exchange"), ("Event Contributions", "event_contribution")]
        for label, value in types:
            self.incoming_type_filter.addItem(label, value)
        self.incoming_type_filter.currentIndexChanged.connect(self.load_incoming_transactions)
        filter_layout.addWidget(self.incoming_type_filter)
        
        filter_layout.addStretch()
        
        # Search
        self.incoming_search = QLineEdit()
        self.incoming_search.setPlaceholderText("Search by item name...")
        self.incoming_search.returnPressed.connect(self.load_incoming_transactions)
        filter_layout.addWidget(self.incoming_search)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.load_incoming_transactions)
        filter_layout.addWidget(search_btn)
        
        layout.addLayout(filter_layout)
        
        # Transactions table
        self.incoming_table = QTableWidget()
        self.incoming_table.setColumnCount(7)
        self.incoming_table.setHorizontalHeaderLabels([
            "ID", "Date", "Item", "Type", "Status", "From/To", "Actions"
        ])
        self.incoming_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.incoming_table.verticalHeader().setVisible(False)
        self.incoming_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.incoming_table)
        
        # Load initial transactions
        self.load_incoming_transactions()
    
    def setup_outgoing_tab(self):
        """Setup the outgoing transactions tab"""
        layout = QVBoxLayout(self.outgoing_tab)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.outgoing_status_filter = QComboBox()
        self.outgoing_status_filter.addItem("All Statuses", None)
        statuses = [("Pending", "pending"), ("Approved", "approved"), 
                   ("Completed", "completed"), ("Rejected", "rejected"),
                   ("Cancelled", "cancelled")]
        for label, value in statuses:
            self.outgoing_status_filter.addItem(label, value)
        self.outgoing_status_filter.currentIndexChanged.connect(self.load_outgoing_transactions)
        filter_layout.addWidget(self.outgoing_status_filter)
        
        self.outgoing_type_filter = QComboBox()
        self.outgoing_type_filter.addItem("All Types", None)
        types = [("Sales", "sale"), ("Donations", "donation"), 
               ("Exchanges", "exchange"), ("Event Contributions", "event_contribution")]
        for label, value in types:
            self.outgoing_type_filter.addItem(label, value)
        self.outgoing_type_filter.currentIndexChanged.connect(self.load_outgoing_transactions)
        filter_layout.addWidget(self.outgoing_type_filter)
        
        filter_layout.addStretch()
        
        # Search
        self.outgoing_search = QLineEdit()
        self.outgoing_search.setPlaceholderText("Search by item name...")
        self.outgoing_search.returnPressed.connect(self.load_outgoing_transactions)
        filter_layout.addWidget(self.outgoing_search)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.load_outgoing_transactions)
        filter_layout.addWidget(search_btn)
        
        layout.addLayout(filter_layout)
        
        # Transactions table
        self.outgoing_table = QTableWidget()
        self.outgoing_table.setColumnCount(7)
        self.outgoing_table.setHorizontalHeaderLabels([
            "ID", "Date", "Item", "Type", "Status", "From/To", "Actions"
        ])
        self.outgoing_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.outgoing_table.verticalHeader().setVisible(False)
        self.outgoing_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.outgoing_table)
        
        # Load initial transactions
        self.load_outgoing_transactions()
    
    def load_incoming_transactions(self):
        """Load incoming transactions (where current user is seller)"""
        # Clear current transactions
        self.incoming_table.setRowCount(0)
        
        # Build filters
        filters = {'seller_id': self.session['user_id']}
        
        if self.incoming_status_filter.currentData():
            filters['status'] = self.incoming_status_filter.currentData()
        
        if self.incoming_type_filter.currentData():
            filters['transaction_type'] = self.incoming_type_filter.currentData()
        
        if self.incoming_search.text():
            filters['search'] = self.incoming_search.text()
        
        # Get transactions from database
        transactions = self.transaction_model.get_transactions(filters=filters, limit=50)
        
        # Add transactions to table
        for row, transaction in enumerate(transactions):
            self.incoming_table.insertRow(row)
            
            # ID column
            self.incoming_table.setItem(row, 0, QTableWidgetItem(str(transaction['transaction_id'])))
            
            # Date column
            date_item = QTableWidgetItem(transaction['created_at'])
            self.incoming_table.setItem(row, 1, date_item)
            
            # Item column
            self.incoming_table.setItem(row, 2, QTableWidgetItem(transaction['item_title']))
            
            # Type column
            type_map = {
                'sale': 'Sale',
                'donation': 'Donation',
                'exchange': 'Exchange',
                'event_contribution': 'Event Contribution'
            }
            type_text = type_map.get(transaction['transaction_type'], 
                                   transaction['transaction_type'].replace('_', ' ').title())
            self.incoming_table.setItem(row, 3, QTableWidgetItem(type_text))
            
            # Status column with color
            status_item = QTableWidgetItem(transaction['status'].upper())
            status_colors = {
                'pending': QColor('#f39c12'),
                'approved': QColor('#2ecc71'),
                'rejected': QColor('#e74c3c'),
                'completed': QColor('#3498db'),
                'cancelled': QColor('#95a5a6')
            }
            if transaction['status'] in status_colors:
                status_item.setForeground(status_colors[transaction['status']])
            status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.incoming_table.setItem(row, 4, status_item)
            
            # From/To column
            self.incoming_table.setItem(row, 5, QTableWidgetItem(transaction['buyer_full_name']))
            
            # Actions column
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setSpacing(4)
            
            view_btn = QPushButton("View")
            view_btn.clicked.connect(lambda _, txn=transaction: self.view_transaction_details(txn))
            actions_layout.addWidget(view_btn)
            
            self.incoming_table.setCellWidget(row, 6, actions_widget)
    
    def load_outgoing_transactions(self):
        """Load outgoing transactions (where current user is buyer)"""
        # Clear current transactions
        self.outgoing_table.setRowCount(0)
        
        # Build filters
        filters = {'buyer_id': self.session['user_id']}
        
        if self.outgoing_status_filter.currentData():
            filters['status'] = self.outgoing_status_filter.currentData()
        
        if self.outgoing_type_filter.currentData():
            filters['transaction_type'] = self.outgoing_type_filter.currentData()
        
        if self.outgoing_search.text():
            filters['search'] = self.outgoing_search.text()
        
        # Get transactions from database
        transactions = self.transaction_model.get_transactions(filters=filters, limit=50)
        
        # Add transactions to table
        for row, transaction in enumerate(transactions):
            self.outgoing_table.insertRow(row)
            
            # ID column
            self.outgoing_table.setItem(row, 0, QTableWidgetItem(str(transaction['transaction_id'])))
            
            # Date column
            date_item = QTableWidgetItem(transaction['created_at'])
            self.outgoing_table.setItem(row, 1, date_item)
            
            # Item column
            self.outgoing_table.setItem(row, 2, QTableWidgetItem(transaction['item_title']))
            
            # Type column
            type_map = {
                'sale': 'Sale',
                'donation': 'Donation',
                'exchange': 'Exchange',
                'event_contribution': 'Event Contribution'
            }
            type_text = type_map.get(transaction['transaction_type'], 
                                   transaction['transaction_type'].replace('_', ' ').title())
            self.outgoing_table.setItem(row, 3, QTableWidgetItem(type_text))
            
            # Status column with color
            status_item = QTableWidgetItem(transaction['status'].upper())
            status_colors = {
                'pending': QColor('#f39c12'),
                'approved': QColor('#2ecc71'),
                'rejected': QColor('#e74c3c'),
                'completed': QColor('#3498db'),
                'cancelled': QColor('#95a5a6')
            }
            if transaction['status'] in status_colors:
                status_item.setForeground(status_colors[transaction['status']])
            status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.outgoing_table.setItem(row, 4, status_item)
            
            # From/To column
            self.outgoing_table.setItem(row, 5, QTableWidgetItem(transaction['seller_full_name']))
            
            # Actions column
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setSpacing(4)
            
            view_btn = QPushButton("View")
            view_btn.clicked.connect(lambda _, txn=transaction: self.view_transaction_details(txn))
            actions_layout.addWidget(view_btn)
            
            self.outgoing_table.setCellWidget(row, 6, actions_widget)
    
    def view_transaction_details(self, transaction):
        """View transaction details"""
        # Fetch full transaction data if needed
        if not transaction.get('notes'):
            full_transaction = self.transaction_model.get_transaction_by_id(transaction['transaction_id'])
            if full_transaction:
                transaction = full_transaction
        
        dialog = TransactionDetailDialog(self.db_connection, self.session, transaction)
        dialog.status_updated.connect(self.handle_status_updated)
        
        if dialog.exec_() == QDialog.Accepted:
            # Reload transactions in case anything changed
            self.reload_transactions()
    
    def reload_transactions(self):
        """Reload both transaction lists"""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:
            self.load_incoming_transactions()
        else:
            self.load_outgoing_transactions()
    
    def handle_status_updated(self, transaction_id, new_status):
        """Handle transaction status updated signal"""
        # Reload transactions
        self.reload_transactions()
"""
Items view for the School Item Exchange/Donation Application
"""

import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QTabWidget, QFormLayout,
    QTextEdit, QDialog, QFileDialog, QMessageBox, QHeaderView, QDoubleSpinBox,
    QCheckBox, QListWidget, QScrollArea, QFrame
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.models.item import Item
from src.models.transaction import Transaction

class ItemDetailDialog(QDialog):
    """Dialog for showing item details and performing actions like buying/trading"""
    transaction_created = pyqtSignal(int)  # Signal emitted when transaction created
    
    def __init__(self, db_connection, session, item_data, parent=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.session = session
        self.item_data = item_data
        self.item_model = Item(db_connection)
        self.transaction_model = Transaction(db_connection)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        self.setWindowTitle("Item Details")
        self.setMinimumSize(600, 500)
        
        main_layout = QVBoxLayout()
        
        # Item title
        title_label = QLabel(self.item_data['title'])
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # Item details in horizontal layout
        details_layout = QHBoxLayout()
        
        # Left side - image if available
        image_frame = QFrame()
        image_frame.setFixedSize(200, 200)
        image_frame.setFrameShape(QFrame.Box)
        image_frame.setLineWidth(1)
        
        image_layout = QVBoxLayout(image_frame)
        
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        
        # Show image if available, otherwise show placeholder
        if self.item_data.get('images') and len(self.item_data['images']) > 0:
            primary_image = None
            for img in self.item_data['images']:
                if img['is_primary']:
                    primary_image = img['path']
                    break
            
            if primary_image and os.path.exists(primary_image):
                image_label.setPixmap(QPixmap(primary_image).scaled(180, 180, Qt.KeepAspectRatio))
            else:
                image_label.setText("Image not available")
        else:
            image_label.setText("No image available")
        
        image_layout.addWidget(image_label)
        details_layout.addWidget(image_frame)
        
        # Right side - item details
        info_layout = QVBoxLayout()
        
        # Item information in form layout
        form_layout = QFormLayout()
        
        form_layout.addRow("Category:", QLabel(self.item_data['category']))
        form_layout.addRow("Condition:", QLabel(self.item_data['condition']))
        if self.item_data['price']:
            form_layout.addRow("Price:", QLabel(f"${self.item_data['price']}"))
        else:
            form_layout.addRow("Price:", QLabel("Not for sale"))
        form_layout.addRow("Status:", QLabel(self.item_data['status']))
        form_layout.addRow("Owner:", QLabel(self.item_data['owner_full_name']))
        
        info_layout.addLayout(form_layout)
        
        # Item description
        info_layout.addWidget(QLabel("Description:"))
        description = QTextEdit(self.item_data['description'])
        description.setReadOnly(True)
        description.setMaximumHeight(100)
        info_layout.addWidget(description)
        
        # Exchange preferences if any
        if self.item_data['exchange_preferences']:
            info_layout.addWidget(QLabel("Exchange Preferences:"))
            preferences = QTextEdit(self.item_data['exchange_preferences'])
            preferences.setReadOnly(True)
            preferences.setMaximumHeight(60)
            info_layout.addWidget(preferences)
        
        details_layout.addLayout(info_layout)
        main_layout.addLayout(details_layout)
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        # Don't show transaction buttons if the item belongs to the current user
        if self.item_data['user_id'] != self.session['user_id'] and self.item_data['status'] == 'approved':
            
            if self.item_data['price'] is not None and self.item_data['price'] > 0:
                buy_button = QPushButton("Buy Now")
                buy_button.clicked.connect(self.buy_item)
                actions_layout.addWidget(buy_button)
            
            exchange_button = QPushButton("Offer Exchange")
            exchange_button.clicked.connect(self.exchange_item)
            actions_layout.addWidget(exchange_button)
            
            donate_button = QPushButton("Donate")
            donate_button.clicked.connect(self.donate_item)
            actions_layout.addWidget(donate_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        actions_layout.addWidget(close_button)
        
        main_layout.addLayout(actions_layout)
        self.setLayout(main_layout)
    
    def buy_item(self):
        """Handle buy item action"""
        reply = QMessageBox.question(
            self, 'Buy Item',
            f"Are you sure you want to buy this item for ${self.item_data['price']}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message, txn_id = self.transaction_model.create_transaction(
                item_id=self.item_data['item_id'],
                buyer_id=self.session['user_id'],
                txn_type='sale',
                amount=self.item_data['price']
            )
            
            if success:
                QMessageBox.information(self, "Success", "Purchase request sent! The seller will be notified.")
                self.transaction_created.emit(txn_id)
                self.accept()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def exchange_item(self):
        """Handle exchange item action"""
        # Get user's available items
        user_items = self.item_model.get_items(filters={
            'user_id': self.session['user_id'], 
            'status': 'approved'
        })
        
        if not user_items:
            QMessageBox.information(self, "No Items Available", 
                                 "You don't have any approved items to exchange.\n"
                                 "Please create and list some items first.")
            return
        
        # Show item selection dialog
        selected_item = self.select_exchange_item_dialog(user_items)
        if not selected_item:
            return
        
        # Confirm exchange
        reply = QMessageBox.question(
            self, 'Confirm Exchange',
            f"Are you sure you want to offer '{selected_item['title']}' in exchange for '{self.item_data['title']}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Create transaction for exchange
            success, message, txn_id = self.transaction_model.create_transaction(
                item_id=self.item_data['item_id'],
                buyer_id=self.session['user_id'],
                txn_type='exchange',
                amount=0  # No monetary amount for exchanges
            )
            
            if success:
                # Store the offered item ID in notes
                self.transaction_model.update_transaction_notes(
                    txn_id,
                    f"Exchange offer: Item #{selected_item['item_id']} ({selected_item['title']})"
                )
                
                QMessageBox.information(self, "Success", "Exchange offer sent! The owner will be notified.")
                self.transaction_created.emit(txn_id)
                self.accept()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def select_exchange_item_dialog(self, items):
        """Show dialog to select an item to exchange"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Item to Offer")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Select one of your items to offer for exchange:"))
        
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
        
        # def on_select():
        #     rows = table.selectionModel().selectedRows()
        #     if rows:
        #         image_button.clicked.connect(self.add_images)
        #         image_section.addWidget(image_button)
                
        #         main_layout.addLayout(image_section)
                
        #         # Buttons
        #         button_layout = QHBoxLayout()
                
        #         create_button = QPushButton("Create Listing")
        #         create_button.clicked.connect(self.create_item)
        #         button_layout.addWidget(create_button)
                
        #         cancel_button = QPushButton("Cancel")
        #         cancel_button.clicked.connect(self.reject)
        #         button_layout.addWidget(cancel_button)
                
        #         main_layout.addLayout(button_layout)
        #         self.setLayout(main_layout)
    
    def load_categories(self):
        """Load categories from database"""
        categories = self.item_model.get_categories()
        for cat in categories:
            self.category_input.addItem(cat['name'], cat['name'])
    
    def add_images(self):
        """Handle image upload"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg)")
        
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            self.image_paths.extend(selected_files)
            self.images_label.setText(f"{len(self.image_paths)} image(s) selected")
    
    def create_item(self):
        """Create new item listing"""
        title = self.title_input.text().strip()
        category = self.category_input.currentData()
        condition = self.condition_input.currentData()
        price = self.price_input.value() if self.price_input.value() > 0 else None
        description = self.description_input.toPlainText().strip()
        exchange_prefs = self.exchange_input.toPlainText().strip() or None
        
        if not title or not description:
            QMessageBox.warning(self, "Error", "Please enter title and description")
            return
        
        success, message, item_id = self.item_model.create_item(
            title=title,
            description=description,
            category=category,
            condition=condition,
            user_id=self.session['user_id'],
            price=price,
            exchange_preferences=exchange_prefs,
            image_paths=self.image_paths
        )
        
        if success:
            # Submit the item for approval
            self.item_model.submit_for_approval(item_id, self.session['user_id'])
            
            QMessageBox.information(self, "Success", 
                                 "Item created and submitted for approval!\n"
                                 "You will be notified once it's approved.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def donate_item(self):
        """Handle donate item action"""
        reply = QMessageBox.question(
            self, 'Donate Item',
            f"Are you sure you want to donate this item '{self.item_data['title']}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message, txn_id = self.transaction_model.create_transaction(
                item_id=self.item_data['item_id'],
                buyer_id=self.session['user_id'],
                txn_type='donation',
                amount=0  # No monetary amount for donations
            )
            
            if success:
                QMessageBox.information(self, "Success", "Donation request sent! The owner will be notified.")
                self.transaction_created.emit(txn_id)
                self.accept()
            else:
                QMessageBox.warning(self, "Error", message)


class ItemCard(QFrame):
    """Card widget for displaying an item in grid view"""
    clicked = pyqtSignal(dict)
    
    def __init__(self, item_data):
        super().__init__()
        self.item_data = item_data
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        self.setObjectName("itemCard")
        self.setStyleSheet("""
            #itemCard {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #ddd;
            }
            #itemCard:hover {
                border: 1px solid #3498db;
                background-color: #f9f9f9;
            }
        """)
        self.setMinimumSize(200, 250)
        self.setMaximumSize(220, 300)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        
        # Image container
        image_frame = QFrame()
        image_frame.setFixedSize(180, 150)
        
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        
        if self.item_data.get('primary_image') and os.path.exists(self.item_data['primary_image']):
            image_label.setPixmap(QPixmap(self.item_data['primary_image']).scaled(
                180, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
        else:
            image_label.setText("No image")
            image_label.setStyleSheet("background-color: #eee;")
        
        image_layout.addWidget(image_label)
        layout.addWidget(image_frame)
        
        # Title
        title_label = QLabel(self.item_data['title'])
        title_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # Price and category
        info_layout = QHBoxLayout()
        
        if self.item_data.get('price'):
            price_label = QLabel(f"${self.item_data['price']}")
            price_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
            info_layout.addWidget(price_label)
        else:
            price_label = QLabel("No price")
            info_layout.addWidget(price_label)
        
        info_layout.addStretch()
        
        category_label = QLabel(self.item_data['category'])
        category_label.setFont(QFont("Segoe UI", 8))
        info_layout.addWidget(category_label)
        
        layout.addLayout(info_layout)
        
        # Condition
        condition_label = QLabel(f"Condition: {self.item_data['condition']}")
        condition_label.setFont(QFont("Segoe UI", 8))
        layout.addWidget(condition_label)
        
        # Handle mouse events
        self.mousePressEvent = self.on_click
    
    def on_click(self, event):
        """Handle click event"""
        self.clicked.emit(self.item_data)


class ItemsView(QWidget):
    """Items view showing available items and user's items"""
    def __init__(self, db_connection, session):
        super().__init__()
        self.db_connection = db_connection
        self.session = session
        self.item_model = Item(db_connection)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Tab widget for My Items/Browse Items
        self.tab_widget = QTabWidget()
        
        # Tab 1: Browse Items
        self.browse_tab = QWidget()
        self.setup_browse_tab()
        self.tab_widget.addTab(self.browse_tab, "Browse Items")
        
        # Tab 2: My Items
        self.my_items_tab = QWidget()
        self.setup_my_items_tab()
        self.tab_widget.addTab(self.my_items_tab, "My Items")
        
        main_layout.addWidget(self.tab_widget)
        
    def setup_browse_tab(self):
        """Set up browse items tab"""
        layout = QVBoxLayout(self.browse_tab)
        
        # Search/filter tools
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items...")
        self.search_input.returnPressed.connect(self.load_browse_items)
        filter_layout.addWidget(self.search_input)
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories", None)
        categories = self.item_model.get_categories()
        for cat in categories:
            self.category_filter.addItem(cat['name'], cat['name'])
        self.category_filter.currentIndexChanged.connect(self.load_browse_items)
        filter_layout.addWidget(self.category_filter)
        
        self.condition_filter = QComboBox()
        self.condition_filter.addItem("All Conditions", None)
        conditions = [("New", "new"), ("Like New", "like_new"), ("Good", "good"), 
                     ("Fair", "fair"), ("Poor", "poor")]
        for label, value in conditions:
            self.condition_filter.addItem(label, value)
        self.condition_filter.currentIndexChanged.connect(self.load_browse_items)
        filter_layout.addWidget(self.condition_filter)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.load_browse_items)
        filter_layout.addWidget(search_btn)
        
        layout.addLayout(filter_layout)
        
        # Items display area - scrollable grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        self.browse_items_container = QWidget()
        self.browse_layout = QHBoxLayout(self.browse_items_container)
        self.browse_layout.setContentsMargins(0, 0, 0, 0)
        self.browse_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.browse_layout.setSpacing(10)
        
        scroll_area.setWidget(self.browse_items_container)
        layout.addWidget(scroll_area)
        
        # Load initial items
        self.load_browse_items()
    
    def setup_my_items_tab(self):
        """Set up my items tab"""
        layout = QVBoxLayout(self.my_items_tab)
        
        # Create new item button
        new_item_btn = QPushButton("Create New Item")
        new_item_btn.clicked.connect(self.create_new_item)
        layout.addWidget(new_item_btn)
        
        # Status filter
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.my_items_filter = QComboBox()
        self.my_items_filter.addItem("All My Items", None)
        statuses = [("Draft", "draft"), ("Pending", "pending"), ("Approved", "approved"), 
                   ("Sold", "sold"), ("Exchanged", "exchanged"), ("Donated", "donated")]
        for label, value in statuses:
            self.my_items_filter.addItem(label, value)
        self.my_items_filter.currentIndexChanged.connect(self.load_my_items)
        filter_layout.addWidget(self.my_items_filter)
        
        filter_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_my_items)
        filter_layout.addWidget(refresh_btn)
        
        layout.addLayout(filter_layout)
        
        # My items table
        self.my_items_table = QTableWidget()
        self.my_items_table.setColumnCount(6)
        self.my_items_table.setHorizontalHeaderLabels([
            "ID", "Title", "Category", "Price", "Status", "Actions"
        ])
        self.my_items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.my_items_table.verticalHeader().setVisible(False)
        self.my_items_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.my_items_table)
        
        # Load initial items
        self.load_my_items()
    
    def load_browse_items(self):
        """Load items for browsing"""
        # Clear current items
        for i in reversed(range(self.browse_layout.count())):
            self.browse_layout.itemAt(i).widget().setParent(None)
        
        # Build filters
        filters = {'status': 'approved'}
        
        if self.search_input.text():
            filters['search'] = self.search_input.text()
        
        if self.category_filter.currentData():
            filters['category'] = self.category_filter.currentData()
        
        if self.condition_filter.currentData():
            filters['condition'] = self.condition_filter.currentData()
        
        # Get items from database
        items = self.item_model.get_items(filters=filters, limit=50)
        
        # Add items to layout
        for item in items:
            item_card = ItemCard(item)
            item_card.clicked.connect(self.show_item_details)
            self.browse_layout.addWidget(item_card)
        
        # Add a "no items" message if no items found
        if not items:
            no_items = QLabel("No items found matching your search criteria.")
            no_items.setAlignment(Qt.AlignCenter)
            self.browse_layout.addWidget(no_items)
    
    def load_my_items(self):
        """Load user's items"""
        # Clear current items
        self.my_items_table.setRowCount(0)
        
        # Build filters
        filters = {'user_id': self.session['user_id']}
        
        if self.my_items_filter.currentData():
            filters['status'] = self.my_items_filter.currentData()
        
        # Get items from database
        items = self.item_model.get_items(filters=filters, limit=50)
        
        # Add items to table
        for row, item in enumerate(items):
            self.my_items_table.insertRow(row)
            
            self.my_items_table.setItem(row, 0, QTableWidgetItem(str(item['item_id'])))
            self.my_items_table.setItem(row, 1, QTableWidgetItem(item['title']))
            self.my_items_table.setItem(row, 2, QTableWidgetItem(item['category']))
            
            price_text = f"${item['price']}" if item['price'] else "N/A"
            self.my_items_table.setItem(row, 3, QTableWidgetItem(price_text))
            
            status_item = QTableWidgetItem(item['status'])
            self.my_items_table.setItem(row, 4, status_item)
            
            # Add action buttons based on status
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            view_btn = QPushButton("View")
            view_btn.clicked.connect(lambda _, item=item: self.show_item_details(item))
            actions_layout.addWidget(view_btn)
            
            if item['status'] == 'draft':
                edit_btn = QPushButton("Edit")
                # edit_btn.clicked.connect(lambda _, item=item: self.edit_item(item))
                actions_layout.addWidget(edit_btn)
                
                submit_btn = QPushButton("Submit")
                submit_btn.clicked.connect(lambda _, item_id=item['item_id']: self.submit_item(item_id))
                actions_layout.addWidget(submit_btn)
            
            if item['status'] in ['draft', 'pending', 'approved']:
                delete_btn = QPushButton("Delete")
                delete_btn.clicked.connect(lambda _, item_id=item['item_id']: self.delete_item(item_id))
                actions_layout.addWidget(delete_btn)
            
            self.my_items_table.setCellWidget(row, 5, actions_widget)
    
    def show_item_details(self, item_data):
        """Show item details dialog"""
        # If we only have summary data, fetch full item data
        if not item_data.get('description'):
            full_item = self.item_model.get_item_by_id(item_data['item_id'])
            if full_item:
                item_data = full_item
            else:
                QMessageBox.warning(self, "Error", "Could not retrieve item details")
                return
        
        dialog = ItemDetailDialog(self.db_connection, self.session, item_data)
        dialog.transaction_created.connect(self.handle_transaction_created)
        dialog.exec_()
    
    def create_new_item(self):
        """Create a new item"""
        dialog = NewItemDialog(self.db_connection, self.session)
        if dialog.exec_() == QDialog.Accepted:
            self.load_my_items()
    
    def submit_item(self, item_id):
        """Submit an item for approval"""
        success, message = self.item_model.submit_for_approval(item_id, self.session['user_id'])
        
        if success:
            QMessageBox.information(self, "Success", "Item submitted for approval successfully!")
            self.load_my_items()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def delete_item(self, item_id):
        """Delete an item"""
        reply = QMessageBox.question(
            self, 'Delete Item',
            "Are you sure you want to delete this item? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.item_model.delete_item(item_id, self.session['user_id'])
            
            if success:
                QMessageBox.information(self, "Success", "Item deleted successfully!")
                self.load_my_items()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def handle_transaction_created(self, txn_id):
        """Handle transaction created signal from item details dialog"""
        # Could refresh some UI elements or show notification
        pass


class NewItemDialog(QDialog):
    """Dialog for creating a new item listing"""
    
    def __init__(self, db_connection, session):
        super().__init__()
        self.db_connection = db_connection
        self.session = session
        self.item_model = Item(db_connection)
        self.image_paths = []
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        self.setWindowTitle("Create New Item")
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout()
        
        # Form layout for item details
        form_layout = QFormLayout()
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter item title")
        form_layout.addRow("Title:", self.title_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Describe your item including condition, features, usage history, etc.")
        self.description_input.setMinimumHeight(100)
        form_layout.addRow("Description:", self.description_input)
        
        # Category dropdown
        self.category_input = QComboBox()
        categories = self.item_model.get_categories()
        for cat in categories:
            # Use name for display and name for data as well
            self.category_input.addItem(cat['name'], cat['name'])
        form_layout.addRow("Category:", self.category_input)
        
        # Condition dropdown
        self.condition_input = QComboBox()
        conditions = [
            ("New", "new"), 
            ("Like New", "like_new"), 
            ("Good", "good"), 
            ("Fair", "fair"), 
            ("Poor", "poor")
        ]
        for label, value in conditions:
            self.condition_input.addItem(label, value)
        form_layout.addRow("Condition:", self.condition_input)
        
        # Price
        price_layout = QHBoxLayout()
        
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 1000)
        self.price_input.setSingleStep(0.5)
        self.price_input.setPrefix("$")
        price_layout.addWidget(self.price_input)
        
        self.is_free = QCheckBox("Free / Donation")
        self.is_free.stateChanged.connect(self.toggle_price)
        price_layout.addWidget(self.is_free)
        
        form_layout.addRow("Price:", price_layout)
        
        # Exchange preferences
        self.exchange_input = QTextEdit()
        self.exchange_input.setPlaceholderText("Items you would consider accepting in exchange (optional)")
        self.exchange_input.setMaximumHeight(50)
        form_layout.addRow("Exchange Preferences:", self.exchange_input)
        
        # Images
        images_layout = QVBoxLayout()
        
        # Image list
        self.image_list = QListWidget()
        self.image_list.setMinimumHeight(100)
        self.image_list.setMaximumHeight(150)
        images_layout.addWidget(self.image_list)
        
        # Image buttons
        image_buttons = QHBoxLayout()
        
        add_image_btn = QPushButton("Add Images")
        add_image_btn.clicked.connect(self.add_images)
        image_buttons.addWidget(add_image_btn)
        
        remove_image_btn = QPushButton("Remove Selected")
        remove_image_btn.clicked.connect(self.remove_image)
        image_buttons.addWidget(remove_image_btn)
        
        set_primary_btn = QPushButton("Set as Primary")
        set_primary_btn.clicked.connect(self.set_primary_image)
        image_buttons.addWidget(set_primary_btn)
        
        # Debug label to show selected files
        self.images_label = QLabel("No images selected")
        images_layout.addWidget(self.images_label)
        
        images_layout.addLayout(image_buttons)
        form_layout.addRow("Images:", images_layout)
        
        layout.addLayout(form_layout)
        
        # Button box
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        
        self.save_btn = QPushButton("Save as Draft")
        self.save_btn.clicked.connect(lambda: self.create_item(submit=False))
        button_layout.addWidget(self.save_btn)
        
        self.submit_btn = QPushButton("Create & Submit")
        self.submit_btn.clicked.connect(lambda: self.create_item(submit=True))
        self.submit_btn.setDefault(True)
        button_layout.addWidget(self.submit_btn)
        
        layout.addLayout(button_layout)
        
        # Set the main layout for the dialog
        self.setLayout(layout)
    
    def toggle_price(self, state):
        """Toggle price input based on free checkbox"""
        self.price_input.setEnabled(not state)
        if state:
            self.price_input.setValue(0)
    
    def add_images(self):
        """Open file dialog to select images"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Item Images", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_paths:
            for path in file_paths:
                # Check if already added
                existing_items = [self.image_list.item(i).text() for i in range(self.image_list.count())]
                if path not in existing_items:
                    self.image_paths.append(path)
                    self.image_list.addItem(path)
    
    def remove_image(self):
        """Remove selected image from list"""
        selected = self.image_list.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        path = item.text()
        
        # Remove from list and paths
        row = self.image_list.row(item)
        self.image_list.takeItem(row)
        self.image_paths.remove(path)
    
    def set_primary_image(self):
        """Set selected image as primary (will be first in list)"""
        selected = self.image_list.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        path = item.text()
        
        # Remove from current position
        row = self.image_list.row(item)
        self.image_list.takeItem(row)
        self.image_paths.remove(path)
        
        # Add to beginning
        self.image_paths.insert(0, path)
        self.image_list.insertItem(0, path)
        self.image_list.setCurrentRow(0)
    
    def create_item(self, submit=False):
        """Create new item with entered data"""
        # Validate inputs
        title = self.title_input.text().strip()
        description = self.description_input.toPlainText().strip()
        category = self.category_input.currentData()
        condition = self.condition_input.currentData()
        price = self.price_input.value() if not self.is_free.isChecked() else None
        exchange_preferences = self.exchange_input.toPlainText().strip() or None
        
        if not title:
            QMessageBox.warning(self, "Validation Error", "Please enter an item title.")
            return
        
        if not description:
            QMessageBox.warning(self, "Validation Error", "Please enter an item description.")
            return
        
        # Create the item
        success, message, item_id = self.item_model.create_item(
            title=title,
            description=description,
            category=category,
            condition=condition,
            user_id=self.session['user_id'],
            price=price,
            exchange_preferences=exchange_preferences,
            image_paths=self.image_paths
        )
        
        if success:
            if submit and item_id:
                # Submit for approval directly
                self.item_model.submit_for_approval(item_id, self.session['user_id'])
                QMessageBox.information(self, "Success", 
                                     "Item created and submitted for approval!")
            else:
                QMessageBox.information(self, "Success", 
                                     "Item saved as draft. You can submit it later.")
            
            self.accept()
        else:
            QMessageBox.warning(self, "Error", message)
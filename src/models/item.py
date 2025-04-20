"""
Item model class for the School Item Exchange/Donation Application
"""


class Item:
    def __init__(self, db_connection):
        """Initialize Item model with database connection"""
        self.conn = db_connection
        self.cursor = self.conn.cursor()
    
    def create_item(self, title, description, category, condition, user_id, 
                   price=None, exchange_preferences=None, event_id=None, image_paths=None):
        """Create a new item listing"""
        try:
            # Insert new item with initial status as 'draft'
            self.cursor.execute(
                """INSERT INTO Item 
                   (title, description, category, condition, price, status, user_id, 
                    exchange_preferences, event_id) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, description, category, condition, price, 'draft', user_id, 
                 exchange_preferences, event_id)
            )
            
            item_id = self.cursor.lastrowid
            
            # Add images if provided
            if image_paths and isinstance(image_paths, list):
                for i, path in enumerate(image_paths):
                    is_primary = 1 if i == 0 else 0
                    self.cursor.execute(
                        "INSERT INTO ItemImage (item_id, image_path, is_primary) VALUES (?, ?, ?)",
                        (item_id, path, is_primary)
                    )
            
            self.conn.commit()
            return True, "Item created successfully", item_id
        except Exception as e:
            self.conn.rollback()
            return False, f"Error creating item: {str(e)}", None
    
    def submit_for_approval(self, item_id, user_id):
        """Submit an item for approval"""
        try:
            # Check if the item belongs to the user
            self.cursor.execute(
                "SELECT user_id, status FROM Item WHERE item_id = ?",
                (item_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Item not found"
            
            item_user_id, status = result
            
            if item_user_id != user_id:
                return False, "You don't have permission to update this item"
            
            if status != 'draft':
                return False, f"Item is already in '{status}' status"
            
            # Update item status to pending
            self.cursor.execute(
                "UPDATE Item SET status = ? WHERE item_id = ?",
                ('pending', item_id)
            )
            
            # Create notification for moderators about new item
            self.cursor.execute(
                """INSERT INTO Notification 
                   (user_id, content, type, reference_id)
                   SELECT user_id, ?, 'item_approval', ?
                   FROM User WHERE role = 'moderator' OR role = 'admin'""",
                (f"New item '{item_id}' requires approval", item_id)
            )
            
            self.conn.commit()
            return True, "Item submitted for approval"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error submitting item: {str(e)}"
    
    def approve_item(self, item_id, moderator_id):
        """Approve an item (moderator/admin only)"""
        try:
            # Check if the user is moderator/admin
            self.cursor.execute(
                "SELECT role FROM User WHERE user_id = ?",
                (moderator_id,)
            )
            role = self.cursor.fetchone()
            
            if not role or role[0] not in ['moderator', 'admin']:
                return False, "You don't have permission to approve items"
            
            # Check if item is in pending status
            self.cursor.execute(
                "SELECT user_id, status FROM Item WHERE item_id = ?",
                (item_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Item not found"
            
            item_user_id, status = result
            
            if status != 'pending':
                return False, f"Item is not pending approval, current status is '{status}'"
            
            # Update item status to approved
            self.cursor.execute(
                "UPDATE Item SET status = ? WHERE item_id = ?",
                ('approved', item_id)
            )
            
            # Notify the item owner
            self.cursor.execute(
                """INSERT INTO Notification 
                   (user_id, content, type, reference_id)
                   VALUES (?, ?, 'item_status', ?)""",
                (item_user_id, f"Your item has been approved and is now listed", item_id)
            )
            
            self.conn.commit()
            return True, "Item approved successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error approving item: {str(e)}"
    
    def reject_item(self, item_id, moderator_id, reason):
        """Reject an item (moderator/admin only)"""
        try:
            # Check if the user is moderator/admin
            self.cursor.execute(
                "SELECT role FROM User WHERE user_id = ?",
                (moderator_id,)
            )
            role = self.cursor.fetchone()
            
            if not role or role[0] not in ['moderator', 'admin']:
                return False, "You don't have permission to reject items"
            
            # Check if item is in pending status
            self.cursor.execute(
                "SELECT user_id, status FROM Item WHERE item_id = ?",
                (item_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Item not found"
            
            item_user_id, status = result
            
            if status != 'pending':
                return False, f"Item is not pending approval, current status is '{status}'"
            
            # Update item status back to draft
            self.cursor.execute(
                "UPDATE Item SET status = ? WHERE item_id = ?",
                ('draft', item_id)
            )
            
            # Notify the item owner
            self.cursor.execute(
                """INSERT INTO Notification 
                   (user_id, content, type, reference_id)
                   VALUES (?, ?, 'item_status', ?)""",
                (item_user_id, f"Your item was not approved. Reason: {reason}", item_id)
            )
            
            self.conn.commit()
            return True, "Item rejected successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error rejecting item: {str(e)}"
    
    def get_item_by_id(self, item_id):
        """Get item details by ID"""
        try:
            self.cursor.execute(
                """SELECT i.item_id, i.title, i.description, i.category, i.condition,
                   i.price, i.status, i.user_id, i.created_at, i.event_id,
                   i.exchange_preferences, u.username, u.full_name
                   FROM Item i
                   JOIN User u ON i.user_id = u.user_id
                   WHERE i.item_id = ?""",
                (item_id,)
            )
            item = self.cursor.fetchone()
            
            if not item:
                return None
            
            # Get item images
            self.cursor.execute(
                "SELECT image_id, image_path, is_primary FROM ItemImage WHERE item_id = ? ORDER BY is_primary DESC",
                (item_id,)
            )
            images = self.cursor.fetchall()
            
            item_data = {
                'item_id': item[0],
                'title': item[1],
                'description': item[2],
                'category': item[3],
                'condition': item[4],
                'price': item[5],
                'status': item[6],
                'user_id': item[7],
                'created_at': item[8],
                'event_id': item[9],
                'exchange_preferences': item[10],
                'owner_username': item[11],
                'owner_full_name': item[12],
                'images': [{'image_id': img[0], 'path': img[1], 'is_primary': img[2]} for img in images]
            }
            
            return item_data
        except Exception as e:
            print(f"Error fetching item: {str(e)}")
            return None
    
    def update_item(self, item_id, user_id, **kwargs):
        """Update item information"""
        try:
            # Check if the item belongs to the user and is in draft status
            self.cursor.execute(
                "SELECT user_id, status FROM Item WHERE item_id = ?",
                (item_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Item not found"
            
            item_user_id, status = result
            
            if item_user_id != user_id:
                return False, "You don't have permission to update this item"
            
            if status != 'draft':
                return False, f"Cannot update item in '{status}' status"
            
            # Build update query dynamically based on provided fields
            fields = []
            values = []
            
            allowed_fields = ['title', 'description', 'category', 'condition', 'price', 'exchange_preferences']
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    fields.append(f"{field} = ?")
                    values.append(value)
            
            if not fields:
                return False, "No valid fields to update"
            
            # Add item_id to values
            values.append(item_id)
            
            # Execute update query
            self.cursor.execute(
                f"UPDATE Item SET {', '.join(fields)} WHERE item_id = ?",
                tuple(values)
            )
            self.conn.commit()
            return True, "Item updated successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error updating item: {str(e)}"
    
    def delete_item(self, item_id, user_id):
        """Delete an item listing"""
        try:
            # Check if the item belongs to the user
            self.cursor.execute(
                "SELECT user_id, status FROM Item WHERE item_id = ?",
                (item_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Item not found"
            
            item_user_id, status = result
            
            # Check if user is owner or admin
            self.cursor.execute(
                "SELECT role FROM User WHERE user_id = ?",
                (user_id,)
            )
            user_role = self.cursor.fetchone()[0]
            
            if item_user_id != user_id and user_role != 'admin':
                return False, "You don't have permission to delete this item"
            
            if status not in ['draft', 'pending', 'approved']:
                return False, f"Cannot delete item in '{status}' status"
            
            # Delete associated images
            self.cursor.execute(
                "DELETE FROM ItemImage WHERE item_id = ?",
                (item_id,)
            )
            
            # Delete item
            self.cursor.execute(
                "DELETE FROM Item WHERE item_id = ?",
                (item_id,)
            )
            
            self.conn.commit()
            return True, "Item deleted successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error deleting item: {str(e)}"
    
    def get_items(self, filters=None, sort_by='created_at', order='DESC', limit=20, offset=0):
        """Get items with optional filtering and sorting"""
        try:
            query = """
                SELECT i.item_id, i.title, i.category, i.condition, i.price, i.status, 
                i.user_id, i.created_at, u.username, u.full_name
                FROM Item i
                JOIN User u ON i.user_id = u.user_id
            """
            
            # Filter parameters
            params = []
            where_clauses = []
            
            if filters:
                if 'status' in filters:
                    where_clauses.append("i.status = ?")
                    params.append(filters['status'])
                
                if 'category' in filters:
                    where_clauses.append("i.category = ?")
                    params.append(filters['category'])
                
                if 'condition' in filters:
                    where_clauses.append("i.condition = ?")
                    params.append(filters['condition'])
                
                if 'user_id' in filters:
                    where_clauses.append("i.user_id = ?")
                    params.append(filters['user_id'])
                
                if 'event_id' in filters:
                    where_clauses.append("i.event_id = ?")
                    params.append(filters['event_id'])
                
                if 'price_min' in filters:
                    where_clauses.append("i.price >= ?")
                    params.append(filters['price_min'])
                
                if 'price_max' in filters:
                    where_clauses.append("i.price <= ?")
                    params.append(filters['price_max'])
                
                if 'search' in filters:
                    search_term = f"%{filters['search']}%"
                    where_clauses.append("(i.title LIKE ? OR i.description LIKE ?)")
                    params.extend([search_term, search_term])
            
            # Default to showing only approved items unless specifically requested
            if not filters or 'status' not in filters:
                where_clauses.append("i.status = 'approved'")
            
            # Add WHERE clauses if any
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            # Add sorting
            valid_sort_fields = {'created_at', 'price', 'title'}
            valid_orders = {'ASC', 'DESC'}
            
            # Use defaults if invalid inputs
            if sort_by not in valid_sort_fields:
                sort_by = 'created_at'
                
            if order not in valid_orders:
                order = 'DESC'
            
            query += f" ORDER BY i.{sort_by} {order}"
            
            # Add pagination
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # Execute query
            self.cursor.execute(query, tuple(params))
            items = self.cursor.fetchall()
            
            # Get primary image for each item
            result = []
            for item in items:
                self.cursor.execute(
                    """SELECT image_path FROM ItemImage 
                       WHERE item_id = ? AND is_primary = 1 
                       LIMIT 1""",
                    (item[0],)
                )
                image = self.cursor.fetchone()
                
                result.append({
                    'item_id': item[0],
                    'title': item[1],
                    'category': item[2],
                    'condition': item[3],
                    'price': item[4],
                    'status': item[5],
                    'user_id': item[6],
                    'created_at': item[7],
                    'owner_username': item[8],
                    'owner_full_name': item[9],
                    'primary_image': image[0] if image else None
                })
            
            return result
        except Exception as e:
            print(f"Error fetching items: {str(e)}")
            return []
    
    def get_pending_items(self, limit=20, offset=0):
        """Get items pending approval (for moderators/admins)"""
        return self.get_items(filters={'status': 'pending'}, limit=limit, offset=offset)
    
    def get_categories(self):
        """Get all active item categories"""
        try:
            self.cursor.execute(
                "SELECT category_id, name, description FROM Category WHERE is_active = 1"
            )
            categories = self.cursor.fetchall()
            
            result = []
            for cat in categories:
                result.append({
                    'category_id': cat[0],
                    'name': cat[1],
                    'description': cat[2]
                })
            
            return result
        except Exception as e:
            print(f"Error fetching categories: {str(e)}")
            return []
    
    def add_item_to_event(self, item_id, event_id, user_id):
        """Add an item to a fundraising/donation event"""
        try:
            # Check if the item belongs to the user and is in approved status
            self.cursor.execute(
                "SELECT user_id, status FROM Item WHERE item_id = ?",
                (item_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Item not found"
            
            item_user_id, status = result
            
            if item_user_id != user_id:
                return False, "You don't have permission to modify this item"
            
            if status != 'approved':
                return False, "Only approved items can be added to events"
            
            # Check if the event exists and is active
            self.cursor.execute(
                "SELECT status FROM Event WHERE event_id = ?",
                (event_id,)
            )
            event = self.cursor.fetchone()
            
            if not event:
                return False, "Event not found"
            
            if event[0] != 'active':
                return False, "Items can only be added to active events"
            
            # Add item to event
            self.cursor.execute(
                "UPDATE Item SET event_id = ? WHERE item_id = ?",
                (event_id, item_id)
            )
            
            # Create notification for event organizer
            self.cursor.execute(
                """INSERT INTO Notification 
                   (user_id, content, type, reference_id)
                   SELECT organizer_id, ?, 'event_contribution', ?
                   FROM Event WHERE event_id = ?""",
                (f"New item contribution to your event", event_id, event_id)
            )
            
            self.conn.commit()
            return True, "Item added to event successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error adding item to event: {str(e)}"
    
    def add_item_image(self, item_id, image_path, is_primary=False):
        """Add an image to an item"""
        try:
            # If this is a primary image, update all other images to non-primary
            if is_primary:
                self.cursor.execute(
                    "UPDATE ItemImage SET is_primary = 0 WHERE item_id = ?",
                    (item_id,)
                )
            
            # Add new image
            self.cursor.execute(
                "INSERT INTO ItemImage (item_id, image_path, is_primary) VALUES (?, ?, ?)",
                (item_id, image_path, 1 if is_primary else 0)
            )
            
            self.conn.commit()
            return True, "Image added successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error adding image: {str(e)}"
    
    def remove_item_image(self, image_id, user_id):
        """Remove an image from an item"""
        try:
            # Check if the image belongs to an item owned by the user
            self.cursor.execute(
                """SELECT i.user_id, im.item_id, im.is_primary
                   FROM ItemImage im
                   JOIN Item i ON im.item_id = i.item_id
                   WHERE im.image_id = ?""",
                (image_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Image not found"
            
            item_user_id, item_id, is_primary = result
            
            # Check if user is owner or admin
            self.cursor.execute(
                "SELECT role FROM User WHERE user_id = ?",
                (user_id,)
            )
            user_role = self.cursor.fetchone()[0]
            
            if item_user_id != user_id and user_role != 'admin':
                return False, "You don't have permission to delete this image"
            
            # Delete the image
            self.cursor.execute(
                "DELETE FROM ItemImage WHERE image_id = ?",
                (image_id,)
            )
            
            # If deleted image was primary, set another image as primary if available
            if is_primary:
                self.cursor.execute(
                    """UPDATE ItemImage SET is_primary = 1
                       WHERE item_id = ? AND image_id = 
                       (SELECT MIN(image_id) FROM ItemImage WHERE item_id = ?)""",
                    (item_id, item_id)
                )
            
            self.conn.commit()
            return True, "Image removed successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error removing image: {str(e)}"
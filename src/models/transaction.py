"""
Transaction model class for the School Item Exchange/Donation Application
"""

from datetime import datetime

class Transaction:
    def __init__(self, db_connection):
        """Initialize Transaction model with database connection"""
        self.conn = db_connection
        self.cursor = self.conn.cursor()
    
    def create_transaction(self, item_id, buyer_id, txn_type, amount=None, event_id=None):
        """Create a new transaction for buying/exchanging/donating an item"""
        try:
            # Check if item exists and is available
            self.cursor.execute(
                "SELECT user_id, status FROM Item WHERE item_id = ?",
                (item_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Item not found", None
            
            seller_id, status = result
            
            # Check if item is available
            if status != 'approved':
                return False, f"Item is not available for transaction (status: {status})", None
            
            # Check if buyer is not the seller
            if buyer_id == seller_id and txn_type != 'event_contribution':
                return False, "You cannot create a transaction for your own item", None
            
            # Calculate fee if applicable (only for sales)
            fee = 0
            if txn_type == 'sale' and amount and amount > 0:
                fee = round(amount * 0.05, 2)  # 5% transaction fee
            
            # Create the transaction
            self.cursor.execute(
                """INSERT INTO TransactionRecord 
                   (seller_id, buyer_id, item_id, event_id, type, amount, fee, status) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (seller_id, buyer_id, item_id, event_id, txn_type, amount, fee, 'pending')
            )
            
            txn_id = self.cursor.lastrowid
            
            # Update item status to reflect pending transaction
            self.cursor.execute(
                "UPDATE Item SET status = 'pending' WHERE item_id = ?",
                (item_id,)
            )
            
            # Notify seller about the transaction
            self.cursor.execute(
                """INSERT INTO Notification 
                   (user_id, content, type, reference_id)
                   VALUES (?, ?, 'transaction', ?)""",
                (seller_id, f"You have a new {txn_type} transaction request", txn_id)
            )
            
            self.conn.commit()
            return True, f"Transaction created successfully", txn_id
        except Exception as e:
            self.conn.rollback()
            return False, f"Error creating transaction: {str(e)}", None
    
    def get_transaction_by_id(self, txn_id):
        """Get transaction details by ID"""
        try:
            self.cursor.execute(
                """SELECT t.txn_id, t.seller_id, t.buyer_id, t.item_id, t.event_id, 
                   t.type, t.amount, t.fee, t.status, t.created_at, t.completed_at, t.notes,
                   i.title as item_title, i.category, i.condition,
                   s.username as seller_username, s.full_name as seller_name,
                   b.username as buyer_username, b.full_name as buyer_name
                   FROM TransactionRecord t
                   JOIN Item i ON t.item_id = i.item_id
                   JOIN User s ON t.seller_id = s.user_id
                   JOIN User b ON t.buyer_id = b.user_id
                   WHERE t.txn_id = ?""",
                (txn_id,)
            )
            txn = self.cursor.fetchone()
            
            if not txn:
                return None
            
            # Get item primary image if available
            self.cursor.execute(
                """SELECT image_path FROM ItemImage 
                   WHERE item_id = ? AND is_primary = 1 
                   LIMIT 1""",
                (txn[3],)  # item_id
            )
            image = self.cursor.fetchone()
            
            transaction_data = {
                'txn_id': txn[0],
                'seller_id': txn[1],
                'buyer_id': txn[2],
                'item_id': txn[3],
                'event_id': txn[4],
                'type': txn[5],
                'amount': txn[6],
                'fee': txn[7],
                'status': txn[8],
                'created_at': txn[9],
                'completed_at': txn[10],
                'notes': txn[11],
                'item_title': txn[12],
                'category': txn[13],
                'condition': txn[14],
                'seller_username': txn[15],
                'seller_name': txn[16],
                'buyer_username': txn[17],
                'buyer_name': txn[18],
                'item_image': image[0] if image else None
            }
            
            return transaction_data
        except Exception as e:
            print(f"Error fetching transaction: {str(e)}")
            return None
    
    def update_transaction_notes(self, txn_id, notes):
        """Update transaction notes"""
        try:
            self.cursor.execute(
                "UPDATE TransactionRecord SET notes = ? WHERE txn_id = ?",
                (notes, txn_id)
            )
            self.conn.commit()
            return True, "Transaction notes updated successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error updating transaction notes: {str(e)}"
    
    def confirm_transaction(self, txn_id, user_id):
        """Confirm a transaction by the seller"""
        try:
            # Check if transaction exists
            self.cursor.execute(
                """SELECT t.seller_id, t.buyer_id, t.item_id, t.status, t.type,
                   i.status as item_status
                   FROM TransactionRecord t
                   JOIN Item i ON t.item_id = i.item_id
                   WHERE t.txn_id = ?""",
                (txn_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Transaction not found"
            
            seller_id, buyer_id, item_id, txn_status, txn_type, item_status = result
            
            # Check if user is the seller
            if user_id != seller_id:
                return False, "You don't have permission to confirm this transaction"
            
            # Check if transaction is pending
            if txn_status != 'pending':
                return False, f"Transaction cannot be confirmed in '{txn_status}' status"
            
            # Update transaction status to completed
            self.cursor.execute(
                "UPDATE TransactionRecord SET status = ?, completed_at = ? WHERE txn_id = ?",
                ('completed', datetime.now(), txn_id)
            )
            
            # Update item status based on transaction type
            new_status = {
                'sale': 'sold',
                'exchange': 'exchanged',
                'donation': 'donated',
                'event_contribution': 'donated'
            }.get(txn_type, 'sold')
            
            self.cursor.execute(
                "UPDATE Item SET status = ? WHERE item_id = ?",
                (new_status, item_id)
            )
            
            # Notify buyer that transaction is confirmed
            self.cursor.execute(
                """INSERT INTO Notification 
                   (user_id, content, type, reference_id)
                   VALUES (?, ?, 'transaction', ?)""",
                (buyer_id, f"Your {txn_type} transaction has been confirmed", txn_id)
            )
            
            self.conn.commit()
            return True, "Transaction confirmed successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error confirming transaction: {str(e)}"
    
    def cancel_transaction(self, txn_id, user_id, reason=None):
        """Cancel a transaction"""
        try:
            # Check if transaction exists
            self.cursor.execute(
                """SELECT t.seller_id, t.buyer_id, t.item_id, t.status, t.type,
                   i.status as item_status 
                   FROM TransactionRecord t
                   JOIN Item i ON t.item_id = i.item_id
                   WHERE t.txn_id = ?""",
                (txn_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Transaction not found"
            
            seller_id, buyer_id, item_id, txn_status, txn_type, item_status = result
            
            # Check if user is involved in transaction
            if user_id != seller_id and user_id != buyer_id:
                # Check if user is admin
                self.cursor.execute(
                    "SELECT role FROM User WHERE user_id = ?",
                    (user_id,)
                )
                role = self.cursor.fetchone()[0]
                
                if role != 'admin':
                    return False, "You don't have permission to cancel this transaction"
            
            # Check if transaction is pending
            if txn_status != 'pending':
                return False, f"Transaction cannot be cancelled in '{txn_status}' status"
            
            # Update transaction status to cancelled
            self.cursor.execute(
                "UPDATE TransactionRecord SET status = ? WHERE txn_id = ?",
                ('cancelled', txn_id)
            )
            
            # Restore item to approved status
            if item_status == 'pending':
                self.cursor.execute(
                    "UPDATE Item SET status = 'approved' WHERE item_id = ?",
                    (item_id,)
                )
            
            # Notify other party about cancellation
            notify_user_id = buyer_id if user_id == seller_id else seller_id
            
            cancellation_message = f"Transaction has been cancelled"
            if reason:
                cancellation_message += f": {reason}"
            
            self.cursor.execute(
                """INSERT INTO Notification 
                   (user_id, content, type, reference_id)
                   VALUES (?, ?, 'transaction', ?)""",
                (notify_user_id, cancellation_message, txn_id)
            )
            
            self.conn.commit()
            return True, "Transaction cancelled successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error cancelling transaction: {str(e)}"
    
    def get_user_transactions(self, user_id, role='both', status=None, limit=20, offset=0):
        """Get transactions for a user (as buyer, seller, or both)"""
        try:
            query_parts = [
                """SELECT t.txn_id, t.seller_id, t.buyer_id, t.item_id, t.event_id, 
                   t.type, t.amount, t.status, t.created_at,
                   i.title as item_title,
                   s.username as seller_username,
                   b.username as buyer_username
                   FROM TransactionRecord t
                   JOIN Item i ON t.item_id = i.item_id
                   JOIN User s ON t.seller_id = s.user_id
                   JOIN User b ON t.buyer_id = b.user_id
                   WHERE """
            ]
            
            params = []
            
            # Filter by user role in transaction
            if role == 'seller':
                query_parts.append("t.seller_id = ?")
                params.append(user_id)
            elif role == 'buyer':
                query_parts.append("t.buyer_id = ?")
                params.append(user_id)
            else:  # both
                query_parts.append("(t.seller_id = ? OR t.buyer_id = ?)")
                params.extend([user_id, user_id])
            
            # Filter by status if provided
            if status:
                query_parts.append("AND t.status = ?")
                params.append(status)
            
            # Add ordering and pagination
            query_parts.append("ORDER BY t.created_at DESC LIMIT ? OFFSET ?")
            params.extend([limit, offset])
            
            # Execute query
            query = " ".join(query_parts)
            self.cursor.execute(query, tuple(params))
            transactions = self.cursor.fetchall()
            
            result = []
            for txn in transactions:
                result.append({
                    'txn_id': txn[0],
                    'seller_id': txn[1],
                    'buyer_id': txn[2],
                    'item_id': txn[3],
                    'event_id': txn[4],
                    'type': txn[5],
                    'amount': txn[6],
                    'status': txn[7],
                    'created_at': txn[8],
                    'item_title': txn[9],
                    'seller_username': txn[10],
                    'buyer_username': txn[11],
                    'role': 'seller' if txn[1] == user_id else 'buyer'
                })
            
            return result
        except Exception as e:
            print(f"Error fetching user transactions: {str(e)}")
            return []
    
    def get_statistics(self, period=None):
        """Get transaction statistics"""
        try:
            stats = {}
            
            # Define period filter
            date_filter = ""
            params = []
            
            if period == 'week':
                date_filter = "WHERE t.created_at >= date('now', '-7 days')"
            elif period == 'month':
                date_filter = "WHERE t.created_at >= date('now', '-1 month')"
            elif period == 'year':
                date_filter = "WHERE t.created_at >= date('now', '-1 year')"
            
            # Get transaction count by type and status
            self.cursor.execute(
                f"""SELECT t.type, t.status, COUNT(*) 
                   FROM TransactionRecord t
                   {date_filter}
                   GROUP BY t.type, t.status"""
            )
            type_status_counts = self.cursor.fetchall()
            
            stats['by_type_status'] = {}
            for txn_type, status, count in type_status_counts:
                if txn_type not in stats['by_type_status']:
                    stats['by_type_status'][txn_type] = {}
                stats['by_type_status'][txn_type][status] = count
            
            # Get total fees collected
            self.cursor.execute(
                f"""SELECT COALESCE(SUM(fee), 0) 
                   FROM TransactionRecord
                   {date_filter}
                   WHERE status = 'completed'"""
            )
            total_fees = self.cursor.fetchone()[0]
            stats['total_fees'] = total_fees
            
            # Get transaction volume by category
            self.cursor.execute(
                f"""SELECT i.category, COUNT(*), COALESCE(SUM(t.amount), 0) 
                   FROM TransactionRecord t
                   JOIN Item i ON t.item_id = i.item_id
                   {date_filter}
                   WHERE t.status = 'completed'
                   GROUP BY i.category"""
            )
            category_stats = self.cursor.fetchall()
            
            stats['by_category'] = {}
            for category, count, amount in category_stats:
                stats['by_category'][category] = {
                    'count': count,
                    'value': amount
                }
            
            # Get daily transaction counts
            self.cursor.execute(
                f"""SELECT date(t.created_at) as day, COUNT(*) 
                   FROM TransactionRecord t
                   {date_filter}
                   GROUP BY day
                   ORDER BY day"""
            )
            daily_counts = self.cursor.fetchall()
            
            stats['daily_counts'] = {day: count for day, count in daily_counts}
            
            return stats
        except Exception as e:
            print(f"Error getting transaction statistics: {str(e)}")
            return {"error": str(e)}

    def get_transactions(self, filters=None, sort_by='created_at', order='DESC', limit=20, offset=0):
        """Get transactions with optional filtering and sorting"""
        try:
            query_parts = [
                """SELECT t.txn_id as transaction_id, t.seller_id, t.buyer_id, t.item_id, t.event_id, 
                   t.type as transaction_type, t.amount, t.fee, t.status, t.created_at, t.completed_at,
                   i.title as item_title,
                   s.username as seller_username, s.full_name as seller_full_name,
                   b.username as buyer_username, b.full_name as buyer_full_name
                   FROM TransactionRecord t
                   JOIN Item i ON t.item_id = i.item_id
                   JOIN User s ON t.seller_id = s.user_id
                   JOIN User b ON t.buyer_id = b.user_id
                   WHERE 1=1"""
            ]
            
            params = []
            
            if filters:
                if 'seller_id' in filters:
                    query_parts.append("AND t.seller_id = ?")
                    params.append(filters['seller_id'])
                
                if 'buyer_id' in filters:
                    query_parts.append("AND t.buyer_id = ?")
                    params.append(filters['buyer_id'])
                    
                if 'item_id' in filters:
                    query_parts.append("AND t.item_id = ?")
                    params.append(filters['item_id'])
                
                if 'event_id' in filters:
                    query_parts.append("AND t.event_id = ?")
                    params.append(filters['event_id'])
                
                if 'status' in filters:
                    query_parts.append("AND t.status = ?")
                    params.append(filters['status'])
                
                if 'transaction_type' in filters:
                    query_parts.append("AND t.type = ?")
                    params.append(filters['transaction_type'])
                
                if 'search' in filters:
                    query_parts.append("AND (i.title LIKE ? OR s.username LIKE ? OR b.username LIKE ?)")
                    search_term = f"%{filters['search']}%"
                    params.extend([search_term, search_term, search_term])
            
            # Add sorting
            valid_sort_fields = {'created_at', 'completed_at', 'amount', 'status'}
            valid_orders = {'ASC', 'DESC'}
            
            # Use defaults if invalid inputs
            if sort_by not in valid_sort_fields:
                sort_by = 'created_at'
                
            if order not in valid_orders:
                order = 'DESC'
            
            sort_field = f"t.{sort_by}"
            query_parts.append(f"ORDER BY {sort_field} {order}")
            
            # Add pagination
            query_parts.append("LIMIT ? OFFSET ?")
            params.extend([limit, offset])
            
            # Execute query
            query = " ".join(query_parts)
            self.cursor.execute(query, tuple(params))
            transactions = self.cursor.fetchall()
            
            # Convert to list of dictionaries
            result = []
            for txn in transactions:
                result.append({
                    'transaction_id': txn[0],
                    'seller_id': txn[1],
                    'buyer_id': txn[2],
                    'item_id': txn[3],
                    'event_id': txn[4],
                    'transaction_type': txn[5],
                    'amount': txn[6],
                    'fee': txn[7],
                    'status': txn[8],
                    'created_at': txn[9],
                    'completed_at': txn[10],
                    'item_title': txn[11],
                    'seller_username': txn[12],
                    'seller_full_name': txn[13],
                    'buyer_username': txn[14],
                    'buyer_full_name': txn[15]
                })
            
            return result
        except Exception as e:
            print(f"Error fetching transactions: {str(e)}")
            return []
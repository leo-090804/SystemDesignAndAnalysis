"""
Event model class for the School Item Exchange/Donation Application
"""

from datetime import datetime

class Event:
    def __init__(self, db_connection):
        """Initialize Event model with database connection"""
        self.conn = db_connection
        self.cursor = self.conn.cursor()
    
    def create_event(self, title, description, start_date, end_date, organizer_id, 
                    target=None, image_path=None):
        """Create a new fundraising/donation event"""
        try:
            # Check if the user has permission to create events (teachers, moderators, admins)
            self.cursor.execute(
                "SELECT role FROM User WHERE user_id = ?",
                (organizer_id,)
            )
            user_role = self.cursor.fetchone()
            
            if not user_role or user_role[0] not in ['teacher', 'moderator', 'admin']:
                return False, "You don't have permission to create events", None
            
            # Set initial status: 'upcoming' if it starts in the future, 'active' if it starts today
            current_date = datetime.now()
            start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if isinstance(start_date, str) else start_date
            
            initial_status = 'upcoming' if start_date_obj > current_date else 'active'
            
            # Insert new event
            self.cursor.execute(
                """INSERT INTO Event 
                   (title, description, target, start_date, end_date, status, organizer_id, image_path) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, description, target, start_date, end_date, initial_status, organizer_id, image_path)
            )
            
            event_id = self.cursor.lastrowid
            
            # Notify admin/moderators about new event
            self.cursor.execute(
                """INSERT INTO Notification 
                   (user_id, content, type, reference_id)
                   SELECT user_id, ?, 'new_event', ?
                   FROM User WHERE role IN ('admin', 'moderator')""",
                (f"New event created: {title}", event_id)
            )
            
            self.conn.commit()
            return True, "Event created successfully", event_id
        except Exception as e:
            self.conn.rollback()
            return False, f"Error creating event: {str(e)}", None
    
    def update_event(self, event_id, user_id, **kwargs):
        """Update event information"""
        try:
            # Check if the user has permission to update this event
            self.cursor.execute(
                """SELECT e.organizer_id, e.status, u.role 
                   FROM Event e
                   JOIN User u ON e.organizer_id = u.user_id
                   WHERE e.event_id = ?""",
                (event_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Event not found"
            
            organizer_id, event_status, organizer_role = result
            
            # Also check the role of the user trying to update
            self.cursor.execute("SELECT role FROM User WHERE user_id = ?", (user_id,))
            user_role = self.cursor.fetchone()[0]
            
            # Only organizer or admin can update event
            if organizer_id != user_id and user_role != 'admin':
                return False, "You don't have permission to update this event"
            
            # Cannot update completed or cancelled events
            if event_status in ['completed', 'cancelled']:
                return False, f"Cannot update event in '{event_status}' status"
            
            # Build update query dynamically based on provided fields
            fields = []
            values = []
            
            allowed_fields = ['title', 'description', 'target', 'start_date', 'end_date', 'image_path']
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    fields.append(f"{field} = ?")
                    values.append(value)
            
            # Check if end date is in the past
            if 'end_date' in kwargs:
                end_date = kwargs['end_date']
                end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00')) if isinstance(end_date, str) else end_date
                
                if end_date_obj < datetime.now() and event_status != 'completed':
                    fields.append("status = ?")
                    values.append('completed')
            
            if not fields:
                return False, "No valid fields to update"
            
            # Add event_id to values
            values.append(event_id)
            
            # Execute update query
            self.cursor.execute(
                f"UPDATE Event SET {', '.join(fields)} WHERE event_id = ?",
                tuple(values)
            )
            self.conn.commit()
            return True, "Event updated successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error updating event: {str(e)}"
    
    def cancel_event(self, event_id, user_id, reason=None):
        """Cancel an event"""
        try:
            # Check if the user has permission to cancel this event
            self.cursor.execute(
                """SELECT e.organizer_id, e.status, u.role 
                   FROM Event e
                   JOIN User u ON e.organizer_id = u.user_id
                   WHERE e.event_id = ?""",
                (event_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, "Event not found"
            
            organizer_id, event_status, organizer_role = result
            
            # Also check the role of the user trying to cancel
            self.cursor.execute("SELECT role FROM User WHERE user_id = ?", (user_id,))
            user_role = self.cursor.fetchone()[0]
            
            # Only organizer or admin can cancel event
            if organizer_id != user_id and user_role != 'admin':
                return False, "You don't have permission to cancel this event"
            
            # Cannot cancel completed events
            if event_status == 'completed':
                return False, "Cannot cancel a completed event"
            
            # Cannot cancel already cancelled events
            if event_status == 'cancelled':
                return False, "Event is already cancelled"
            
            # Update event status to cancelled
            self.cursor.execute(
                "UPDATE Event SET status = ? WHERE event_id = ?",
                ('cancelled', event_id)
            )
            
            # Notify all users who have items in this event
            self.cursor.execute(
                """INSERT INTO Notification 
                   (user_id, content, type, reference_id)
                   SELECT DISTINCT i.user_id, ?, 'event_cancelled', ?
                   FROM Item i WHERE i.event_id = ?""",
                (f"Event has been cancelled: {reason if reason else 'No reason provided'}", event_id, event_id)
            )
            
            # Update items in this event to remove event association
            self.cursor.execute(
                "UPDATE Item SET event_id = NULL WHERE event_id = ?",
                (event_id,)
            )
            
            self.conn.commit()
            return True, "Event cancelled successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error cancelling event: {str(e)}"
    
    def get_event_by_id(self, event_id):
        """Get event details by ID"""
        try:
            self.cursor.execute(
                """SELECT e.event_id, e.title, e.description, e.target, e.start_date,
                   e.end_date, e.status, e.organizer_id, e.created_at, e.image_path,
                   u.username, u.full_name
                   FROM Event e
                   JOIN User u ON e.organizer_id = u.user_id
                   WHERE e.event_id = ?""",
                (event_id,)
            )
            event = self.cursor.fetchone()
            
            if not event:
                return None
            
            # Get contributions count and total items
            self.cursor.execute(
                "SELECT COUNT(*), COALESCE(SUM(price), 0) FROM Item WHERE event_id = ?",
                (event_id,)
            )
            contributions = self.cursor.fetchone()
            
            event_data = {
                'event_id': event[0],
                'title': event[1],
                'description': event[2],
                'target': event[3],
                'start_date': event[4],
                'end_date': event[5],
                'status': event[6],
                'organizer_id': event[7],
                'created_at': event[8],
                'image_path': event[9],
                'organizer_username': event[10],
                'organizer_full_name': event[11],
                'contribution_count': contributions[0],
                'contribution_value': contributions[1],
                'progress_percentage': (contributions[1]/event[3]*100) if event[3] and event[3] > 0 else None
            }
            
            return event_data
        except Exception as e:
            print(f"Error fetching event: {str(e)}")
            return None
    
    def get_events(self, filters=None, sort_by='start_date', order='DESC', limit=20, offset=0):
        """Get events with optional filtering and sorting"""
        try:
            query = """
                SELECT e.event_id, e.title, e.description, e.target, e.start_date,
                e.end_date, e.status, e.organizer_id, e.created_at, e.image_path,
                u.username, u.full_name
                FROM Event e
                JOIN User u ON e.organizer_id = u.user_id
            """
            
            # Filter parameters
            params = []
            where_clauses = []
            
            if filters:
                if 'status' in filters:
                    where_clauses.append("e.status = ?")
                    params.append(filters['status'])
                
                if 'organizer_id' in filters:
                    where_clauses.append("e.organizer_id = ?")
                    params.append(filters['organizer_id'])
                
                if 'search' in filters:
                    search_term = f"%{filters['search']}%"
                    where_clauses.append("(e.title LIKE ? OR e.description LIKE ?)")
                    params.extend([search_term, search_term])
                
                # Filter for events that haven't ended yet
                if 'active_only' in filters and filters['active_only']:
                    where_clauses.append("(e.status IN ('upcoming', 'active'))")
                
                # Filter by date range
                if 'date_start' in filters:
                    where_clauses.append("e.end_date >= ?")
                    params.append(filters['date_start'])
                
                if 'date_end' in filters:
                    where_clauses.append("e.start_date <= ?")
                    params.append(filters['date_end'])
            
            # Add WHERE clauses if any
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            # Add sorting
            valid_sort_fields = {'start_date', 'end_date', 'created_at', 'title'}
            valid_orders = {'ASC', 'DESC'}
            
            # Use defaults if invalid inputs
            if sort_by not in valid_sort_fields:
                sort_by = 'start_date'
                
            if order not in valid_orders:
                order = 'DESC'
            
            query += f" ORDER BY e.{sort_by} {order}"
            
            # Add pagination
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # Execute query
            self.cursor.execute(query, tuple(params))
            events = self.cursor.fetchall()
            
            # Get contributions for each event
            result = []
            for event in events:
                self.cursor.execute(
                    "SELECT COUNT(*), COALESCE(SUM(price), 0) FROM Item WHERE event_id = ?",
                    (event[0],)
                )
                contributions = self.cursor.fetchone()
                
                result.append({
                    'event_id': event[0],
                    'title': event[1],
                    'description': event[2],
                    'target': event[3],
                    'start_date': event[4],
                    'end_date': event[5],
                    'status': event[6],
                    'organizer_id': event[7],
                    'created_at': event[8],
                    'image_path': event[9],
                    'organizer_username': event[10],
                    'organizer_full_name': event[11],
                    'contribution_count': contributions[0],
                    'contribution_value': contributions[1],
                    'progress_percentage': (contributions[1]/event[3]*100) if event[3] and event[3] > 0 else None
                })
            
            return result
        except Exception as e:
            print(f"Error fetching events: {str(e)}")
            return []
    
    def get_event_contributions(self, event_id):
        """Get items contributed to an event"""
        try:
            self.cursor.execute(
                """SELECT t.txn_id, t.created_at, 
                   i.item_id, i.title, i.category, i.condition, 
                   u.user_id, u.username, u.full_name
                   FROM TransactionRecord t
                   JOIN Item i ON t.item_id = i.item_id
                   JOIN User u ON i.user_id = u.user_id
                   WHERE t.event_id = ? AND t.type = 'event_contribution'
                   ORDER BY t.created_at DESC""",
                (event_id,)
            )
            contributions = self.cursor.fetchall()
            
            result = []
            for contrib in contributions:
                result.append({
                    'txn_id': contrib[0],
                    'date': contrib[1],
                    'item_id': contrib[2],
                    'title': contrib[3],
                    'category': contrib[4],
                    'condition': contrib[5],
                    'user_id': contrib[6],
                    'username': contrib[7],
                    'full_name': contrib[8]
                })
            
            return result
        except Exception as e:
            print(f"Error fetching event contributions: {str(e)}")
            return []
    
    def update_event_status(self):
        """Update event statuses based on current date (run daily)"""
        try:
            current_date = datetime.now()
            
            # Set events that have started to 'active'
            self.cursor.execute(
                """UPDATE Event SET status = 'active'
                   WHERE status = 'upcoming' AND start_date <= ?""",
                (current_date,)
            )
            
            # Set events that have ended to 'completed'
            self.cursor.execute(
                """UPDATE Event SET status = 'completed'
                   WHERE status = 'active' AND end_date < ?""",
                (current_date,)
            )
            
            self.conn.commit()
            return True, "Event statuses updated successfully"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error updating event statuses: {str(e)}"
    
    def get_statistics(self, event_id=None):
        """Get statistics for events"""
        try:
            stats = {}
            
            if event_id:
                # Get statistics for a specific event
                event = self.get_event_by_id(event_id)
                if not event:
                    return {"error": "Event not found"}
                
                stats['event'] = event
                
                # Get contribution statistics
                self.cursor.execute(
                    """SELECT category, COUNT(*), COALESCE(SUM(price), 0)
                       FROM Item WHERE event_id = ?
                       GROUP BY category""",
                    (event_id,)
                )
                categories = self.cursor.fetchall()
                
                stats['contributions_by_category'] = [
                    {'category': cat[0], 'count': cat[1], 'value': cat[2]}
                    for cat in categories
                ]
                
                # Get daily contribution trend
                self.cursor.execute(
                    """SELECT date(created_at) as day, COUNT(*), COALESCE(SUM(price), 0)
                       FROM Item WHERE event_id = ?
                       GROUP BY day ORDER BY day""",
                    (event_id,)
                )
                daily_stats = self.cursor.fetchall()
                
                stats['daily_contributions'] = [
                    {'day': day[0], 'count': day[1], 'value': day[2]}
                    for day in daily_stats
                ]
            else:
                # Get overall statistics for all events
                self.cursor.execute(
                    """SELECT status, COUNT(*) 
                       FROM Event 
                       GROUP BY status"""
                )
                status_counts = self.cursor.fetchall()
                
                stats['events_by_status'] = {status[0]: status[1] for status in status_counts}
                
                # Get top events by contribution value
                self.cursor.execute(
                    """SELECT e.event_id, e.title, COUNT(i.item_id) as item_count, 
                       COALESCE(SUM(i.price), 0) as total_value
                       FROM Event e
                       LEFT JOIN Item i ON e.event_id = i.event_id
                       GROUP BY e.event_id
                       ORDER BY total_value DESC
                       LIMIT 5"""
                )
                top_events = self.cursor.fetchall()
                
                stats['top_events'] = [
                    {
                        'event_id': event[0], 
                        'title': event[1], 
                        'item_count': event[2], 
                        'total_value': event[3]
                    }
                    for event in top_events
                ]
                
                # Get monthly event statistics
                self.cursor.execute(
                    """SELECT strftime('%Y-%m', start_date) as month, COUNT(*) 
                       FROM Event 
                       GROUP BY month 
                       ORDER BY month"""
                )
                monthly_stats = self.cursor.fetchall()
                
                stats['monthly_events'] = {month[0]: month[1] for month in monthly_stats}
            
            return stats
        except Exception as e:
            print(f"Error getting event statistics: {str(e)}")
            return {"error": str(e)}
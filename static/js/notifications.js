/**
 * Real-time notifications handler for the School Exchange Platform
 */

class NotificationManager {
    constructor(options = {}) {
        this.options = {
            pollInterval: 10000, // Poll every 10 seconds by default
            apiEndpoint: '/api/notifications/recent',
            countEndpoint: '/api/notifications/unread-count',
            markReadEndpoint: '/api/notifications/mark-read',
            markAllReadEndpoint: '/api/notifications/mark-all-read',
            ...options
        };
        
        this.lastCheck = new Date();
        this.notificationBadge = document.querySelector('.notifications-badge');
        this.notificationsList = document.querySelector('.notifications-list');
        this.markAllReadBtn = document.querySelector('.mark-all-read');
        this.notificationsDropdown = document.getElementById('notifications-dropdown');
        
        this.init();
    }
    
    init() {
        if (!this.notificationsDropdown) return;
        
        // Initial load
        this.loadNotificationCount();
        
        // Set up dropdown event listener
        this.notificationsDropdown.addEventListener('show.bs.dropdown', () => this.loadRecentNotifications());
        
        // Set up mark all as read button
        if (this.markAllReadBtn) {
            this.markAllReadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.markAllAsRead();
            });
        }
        
        // Start polling for new notifications
        this.startPolling();
    }
    
    startPolling() {
        this.pollInterval = setInterval(() => {
            this.loadNotificationCount(true);
        }, this.options.pollInterval);
    }
    
    stopPolling() {
        clearInterval(this.pollInterval);
    }
    
    async loadNotificationCount(checkForNew = false) {
        try {
            const response = await fetch(this.options.countEndpoint);
            const data = await response.json();
            
            if (data.count > 0) {
                this.notificationBadge.textContent = data.count > 99 ? '99+' : data.count;
                this.notificationBadge.classList.remove('d-none');
                
                // If we're checking for new notifications and the count increased, show a toast
                if (checkForNew && this.previousCount !== undefined && data.count > this.previousCount) {
                    this.showNewNotificationToast();
                }
                
                this.previousCount = data.count;
            } else {
                this.notificationBadge.classList.add('d-none');
                this.previousCount = 0;
            }
        } catch (error) {
            console.error('Error fetching notification count:', error);
        }
    }
    
    async loadRecentNotifications() {
        if (!this.notificationsList) return;
        
        try {
            // Show loading spinner
            this.notificationsList.innerHTML = `
                <div class="text-center py-3">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
            
            const response = await fetch(this.options.apiEndpoint);
            const data = await response.json();
            
            // Update badge count
            if (data.unread_count > 0) {
                this.notificationBadge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
                this.notificationBadge.classList.remove('d-none');
                this.previousCount = data.unread_count;
            } else {
                this.notificationBadge.classList.add('d-none');
                this.previousCount = 0;
            }
            
            // Update notifications list
            let notificationsHtml = '';
            if (data.notifications.length === 0) {
                notificationsHtml = `
                    <div class="text-center py-3 text-muted">
                        <i class="fas fa-bell-slash fa-2x mb-2"></i>
                        <p>No notifications</p>
                    </div>
                `;
            } else {
                data.notifications.forEach(notification => {
                    const date = new Date(notification.created_at);
                    const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                    const readClass = notification.is_read ? '' : 'bg-light';
                    
                    notificationsHtml += `
                        <div class="dropdown-item notification-item ${readClass}" data-id="${notification.noti_id}" 
                             data-item-id="${notification.related_item_id || ''}" 
                             data-transaction-id="${notification.related_transaction_id || ''}">
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-muted">${formattedDate}</small>
                                ${notification.is_read ? '' : '<span class="badge bg-primary">New</span>'}
                            </div>
                            <p class="mb-1">${notification.message}</p>
                        </div>
                        <div class="dropdown-divider"></div>
                    `;
                });
            }
            
            this.notificationsList.innerHTML = notificationsHtml;
            
            // Add click event listeners to notification items
            document.querySelectorAll('.notification-item').forEach(item => {
                item.addEventListener('click', () => {
                    const notiId = item.getAttribute('data-id');
                    this.markAsRead(notiId);
                    
                    // If there's a related item or transaction, redirect to it
                    const itemId = item.getAttribute('data-item-id');
                    const transactionId = item.getAttribute('data-transaction-id');
                    
                    if (itemId && itemId !== 'null' && itemId !== '') {
                        window.location.href = `/items/${itemId}`;
                    } else if (transactionId && transactionId !== 'null' && transactionId !== '') {
                        window.location.href = `/transactions/${transactionId}`;
                    } else {
                        window.location.href = '/notifications';
                    }
                });
            });
            
        } catch (error) {
            console.error('Error fetching notifications:', error);
            this.notificationsList.innerHTML = `
                <div class="text-center py-3 text-danger">
                    <i class="fas fa-exclamation-circle fa-2x mb-2"></i>
                    <p>Failed to load notifications</p>
                </div>
            `;
        }
    }
    
    async markAsRead(notiId) {
        try {
            await fetch(`${this.options.markReadEndpoint}/${notiId}`, {
                method: 'POST'
            });
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
    }
    
    async markAllAsRead() {
        try {
            const response = await fetch(this.options.markAllReadEndpoint, {
                method: 'POST'
            });
            
            const data = await response.json();
            if (data.success) {
                // Refresh notifications
                this.loadNotificationCount();
                this.loadRecentNotifications();
            }
        } catch (error) {
            console.error('Error marking all notifications as read:', error);
        }
    }
    
    showNewNotificationToast() {
        // If SweetAlert2 is available, use it for the toast
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'info',
                title: 'New Notification',
                text: 'You have received a new notification',
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
        } else {
            // Create a simple toast if SweetAlert2 is not available
            const toast = document.createElement('div');
            toast.className = 'toast-notification';
            toast.innerHTML = `
                <div class="toast-header">
                    <i class="fas fa-bell text-primary me-2"></i>
                    <strong>New Notification</strong>
                </div>
                <div class="toast-body">
                    You have received a new notification
                </div>
            `;
            document.body.appendChild(toast);
            
            // Remove the toast after 3 seconds
            setTimeout(() => {
                toast.classList.add('toast-hide');
                setTimeout(() => {
                    document.body.removeChild(toast);
                }, 300);
            }, 3000);
        }
        
        // Play notification sound if available
        const notificationSound = document.getElementById('notification-sound');
        if (notificationSound) {
            notificationSound.play().catch(e => console.log('Could not play notification sound'));
        }
    }
}

// Initialize the notification manager when the document is ready
document.addEventListener('DOMContentLoaded', function() {
    window.notificationManager = new NotificationManager();
});

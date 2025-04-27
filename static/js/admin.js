/**
 * Admin dashboard functionality for the School Exchange Platform
 */

class AdminDashboard {
    constructor(options = {}) {
        this.options = {
            pollInterval: 15000, // Check every 15 seconds
            pendingItemsEndpoint: '/api/admin/pending-items-count',
            pendingTransactionsEndpoint: '/api/admin/pending-transactions-count',
            ...options
        };
        
        this.lastItemsCount = 0;
        this.lastTransactionsCount = 0;
        
        this.init();
    }
    
    init() {
        // Start checking for pending approvals
        this.checkPendingApprovals();
        
        // Set up polling interval
        setInterval(() => this.checkPendingApprovals(), this.options.pollInterval);
    }
    
    async checkPendingApprovals() {
        try {
            // Check pending items
            const itemsResponse = await fetch(this.options.pendingItemsEndpoint);
            const itemsData = await itemsResponse.json();
            
            // Check pending transactions
            const transactionsResponse = await fetch(this.options.pendingTransactionsEndpoint);
            const transactionsData = await transactionsResponse.json();
            
            // Update UI with new counts
            this.updatePendingItemsUI(itemsData.count);
            this.updatePendingTransactionsUI(transactionsData.count);
            
            // Show alerts for new pending approvals
            if (itemsData.count > this.lastItemsCount && this.lastItemsCount !== 0) {
                const newItems = itemsData.count - this.lastItemsCount;
                this.showNewPendingAlert('item', newItems);
            }
            
            if (transactionsData.count > this.lastTransactionsCount && this.lastTransactionsCount !== 0) {
                const newTransactions = transactionsData.count - this.lastTransactionsCount;
                this.showNewPendingAlert('transaction', newTransactions);
            }
            
            // Update stored counts
            this.lastItemsCount = itemsData.count;
            this.lastTransactionsCount = transactionsData.count;
            
        } catch (error) {
            console.error('Error checking pending approvals:', error);
        }
    }
    
    updatePendingItemsUI(count) {
        const container = document.getElementById('pending-items-container');
        if (!container) return;
        
        if (count > 0) {
            container.innerHTML = `
                <div class="alert alert-primary alert-permanent d-flex align-items-center mb-4">
                    <i class="fas fa-exclamation-circle me-3 fs-4"></i>
                    <div>
                        <strong>${count}</strong> item${count !== 1 ? 's' : ''} waiting for your approval.
                    </div>
                </div>
                <a href="/admin/items/pending" class="btn btn-primary w-100">
                    <i class="fas fa-search me-2"></i> Review Items
                </a>
            `;
        } else {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-check-circle text-success fa-4x mb-3"></i>
                    <h5>No items pending approval</h5>
                    <p class="text-muted">All items have been reviewed.</p>
                </div>
            `;
        }
    }
    
    updatePendingTransactionsUI(count) {
        const container = document.getElementById('pending-transactions-container');
        if (!container) return;
        
        if (count > 0) {
            container.innerHTML = `
                <div class="alert alert-success alert-permanent d-flex align-items-center mb-4">
                    <i class="fas fa-exclamation-circle me-3 fs-4"></i>
                    <div>
                        <strong>${count}</strong> transaction${count !== 1 ? 's' : ''} waiting for your approval.
                    </div>
                </div>
                <a href="/admin/transactions?status=pending" class="btn btn-success w-100">
                    <i class="fas fa-search me-2"></i> Review Transactions
                </a>
            `;
        } else {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-check-circle text-success fa-4x mb-3"></i>
                    <h5>No transactions pending approval</h5>
                    <p class="text-muted">All transactions have been reviewed.</p>
                </div>
            `;
        }
    }
    
    showNewPendingAlert(type, count) {
        // Use SweetAlert2 to show notification
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'warning',
                title: `New Pending ${type === 'item' ? 'Items' : 'Transactions'}`,
                text: `You have ${count} new ${type}${count !== 1 ? 's' : ''} pending approval`,
                toast: true,
                position: 'top-end',
                showConfirmButton: true,
                confirmButtonText: 'Review Now',
                timer: 10000,
                timerProgressBar: true
            }).then((result) => {
                if (result.isConfirmed) {
                    window.location.href = type === 'item' ? 
                        '/admin/items/pending' : 
                        '/admin/transactions?status=pending';
                }
            });
        }
        
        // Play notification sound
        const notificationSound = document.getElementById('notification-sound');
        if (notificationSound) {
            notificationSound.play().catch(e => console.log('Could not play notification sound'));
        }
    }
}

// Initialize the admin dashboard when the document is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.body.classList.contains('admin-dashboard')) {
        window.adminDashboard = new AdminDashboard();
    }
});

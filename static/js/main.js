/**
 * Main JavaScript file for School Exchange Platform
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('School Exchange Platform initialized');
    
    // Initialize tooltips if Bootstrap is being used
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
    
    // Add fade-out effect to regular alerts but exclude special permanent ones
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent):not(.pending-approval-alert):not(.item-rejected-alert)');
    if (alerts.length > 0) {
        alerts.forEach(alert => {
            setTimeout(() => {
                alert.classList.add('fade');
                setTimeout(() => {
                    alert.remove();
                }, 500);
            }, 10000); // Increased from 5000 to 10000 (10 seconds)
        });
    }
});

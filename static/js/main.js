document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Update stats from API
    function updateStats() {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                // Update navbar pending count
                const pendingCountElement = document.querySelector('.pending-count');
                if (pendingCountElement) {
                    const pendingCount = data.pending_applications;
                    if (pendingCount > 0) {
                        pendingCountElement.textContent = pendingCount;
                        pendingCountElement.style.display = 'inline-block';
                    } else {
                        pendingCountElement.style.display = 'none';
                    }
                }
                
                // Update dashboard stats if they exist
                const totalChannelsElement = document.getElementById('total-channels');
                const pendingChannelsElement = document.getElementById('pending-channels');
                const sfwChannelsElement = document.getElementById('sfw-channels');
                const nsfwChannelsElement = document.getElementById('nsfw-channels');
                const totalSubscribersElement = document.getElementById('total-subscribers');
                
                if (totalChannelsElement) totalChannelsElement.textContent = data.total_channels;
                if (pendingChannelsElement) pendingChannelsElement.textContent = data.pending_applications;
                if (sfwChannelsElement) sfwChannelsElement.textContent = data.sfw_channels;
                if (nsfwChannelsElement) nsfwChannelsElement.textContent = data.nsfw_channels;
                if (totalSubscribersElement) totalSubscribersElement.textContent = data.total_subscribers;
                
                // Update the pie chart if it exists
                if (window.channelsChart) {
                    window.channelsChart.data.datasets[0].data = [data.sfw_channels, data.nsfw_channels];
                    window.channelsChart.update();
                }
            })
            .catch(error => console.error('Error fetching stats:', error));
    }
    
    // Run immediately
    updateStats();
    
    // Update every 30 seconds
    setInterval(updateStats, 30000);

    // Auto-dismiss flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(message => {
        setTimeout(() => {
            const closeButton = message.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000);
    });

    // Schedule day toggle functionality
    const dayToggleButtons = document.querySelectorAll('.day-toggle');
    dayToggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const dayCard = this.closest('.day-card');
            dayCard.classList.toggle('active');
            
            const checkbox = dayCard.querySelector('input[type="checkbox"]');
            checkbox.checked = !checkbox.checked;
        });
    });

    // Dark mode toggle
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            
            // Store preference
            const isDarkMode = document.body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDarkMode ? 'true' : 'false');
            
            // Update toggle icon
            const icon = this.querySelector('i');
            if (isDarkMode) {
                icon.classList.remove('bi-moon');
                icon.classList.add('bi-sun');
            } else {
                icon.classList.remove('bi-sun');
                icon.classList.add('bi-moon');
            }
        });
        
        // Check saved preference
        const savedDarkMode = localStorage.getItem('darkMode');
        if (savedDarkMode === 'true') {
            document.body.classList.add('dark-mode');
            const icon = darkModeToggle.querySelector('i');
            icon.classList.remove('bi-moon');
            icon.classList.add('bi-sun');
        }
    }
    
    // Emoji picker functionality (if implemented)
    const emojiPicker = document.getElementById('emoji-picker');
    const emojisInput = document.getElementById('emojis');
    
    if (emojiPicker && emojisInput) {
        const commonEmojis = ['😊', '👍', '❤️', '🔥', '✨', '🎮', '📱', '💻', '🎵', '📚', '🍕', '🎬', '⚽', '🎨', '🚀', '🤔', '😂'];
        
        // Build emoji buttons
        commonEmojis.forEach(emoji => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'emoji-btn';
            button.textContent = emoji;
            button.addEventListener('click', function() {
                const currentValue = emojisInput.value.trim();
                const emojis = currentValue ? currentValue.split(',').map(e => e.trim()) : [];
                
                if (emojis.includes(emoji)) {
                    return; // Emoji already added
                }
                
                if (emojis.length >= 3) {
                    emojis.pop(); // Remove the last emoji if already have 3
                }
                
                emojis.push(emoji);
                emojisInput.value = emojis.join(', ');
            });
            
            emojiPicker.appendChild(button);
        });
    }
});
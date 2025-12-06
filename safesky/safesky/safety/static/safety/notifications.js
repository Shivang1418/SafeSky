// static/js/notifications.js
setInterval(() => {
    fetch('/safety/get_notifications/')
        .then(response => response.json())
        .then(data => {
            if(data.new_notifications.length > 0){
                data.new_notifications.forEach(n => alert(n.message));
            }
        });
}, 5000); // every 5 seconds

(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const feed = document.getElementById('investor-activity-feed');
        if (feed && !feed.children.length) {
            feed.innerHTML = '<div class="text-sm text-white/50">No portfolio activity yet.</div>';
        }
    });
})();

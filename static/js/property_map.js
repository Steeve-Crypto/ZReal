(function () {
    function showFallback(message) {
        const fallback = document.getElementById('property-map-fallback');
        if (fallback) {
            fallback.textContent = message;
            fallback.hidden = false;
        }
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function initMap() {
        const mapElement = document.getElementById('property-map');
        const dataElement = document.getElementById('property-map-data');
        if (!mapElement || !dataElement) {
            return;
        }

        if (typeof L === 'undefined') {
            showFallback('Leaflet did not load. The property list below is still available.');
            return;
        }

        const center = JSON.parse(mapElement.dataset.center || '[51.505,-0.09]');
        const properties = JSON.parse(dataElement.textContent || '[]');
        const map = L.map(mapElement).setView(center, 6);
        const bounds = [];

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors | ZReal on Zcash',
            maxZoom: 19
        }).addTo(map);

        properties.forEach(function (property) {
            if (property.lat === null || property.lng === null) {
                return;
            }
            bounds.push([property.lat, property.lng]);
            const marker = L.marker([property.lat, property.lng]).addTo(map);
            const zsaMarkup = property.zsa_asset_id
                ? `<p><strong>ZSA ID:</strong> <code>${escapeHtml(property.zsa_asset_id)}</code></p>`
                : '';
            const visibilityMarkup = property.visibility === 'issuer_only'
                ? '<p><strong>Visibility:</strong> Issuer-only draft</p>'
                : '<p><strong>Visibility:</strong> Public</p>';
            marker.bindPopup(`
                <div class="property-popup">
                    <h3>${escapeHtml(property.title)}</h3>
                    <p><strong>Address:</strong> ${escapeHtml(property.address)}</p>
                    <p><strong>Size:</strong> ${escapeHtml(property.size_sqm || 'No data yet')} sqm</p>
                    <p><strong>Est. Value:</strong> ${escapeHtml(property.estimated_value || 'No data yet')}</p>
                    <p><strong>Status:</strong> ${escapeHtml(property.status)}</p>
                    ${visibilityMarkup}
                    <p><strong>Total Shares:</strong> ${escapeHtml(property.total_shares)}</p>
                    ${zsaMarkup}
                </div>
            `);
        });

        if (bounds.length) {
            map.fitBounds(bounds, { padding: [32, 32], maxZoom: 12 });
        }

        setTimeout(function () {
            map.invalidateSize();
        }, 0);
    }

    document.addEventListener('DOMContentLoaded', initMap);
})();

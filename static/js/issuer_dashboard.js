(function () {
    function getCsrfToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    function setCheckoutLoading(button, isLoading) {
        if (!button) {
            return;
        }
        button.disabled = isLoading;
        button.innerHTML = isLoading
            ? '<span class="flex items-center justify-center gap-x-3"><i class="fas fa-spinner fa-spin"></i> Redirecting to Stripe...</span>'
            : '<span>Subscribe with Stripe</span><i class="fas fa-arrow-right"></i>';
    }

    async function startStripeCheckout(event) {
        const button = event.currentTarget;
        const checkoutUrl = button.dataset.checkoutUrl;
        setCheckoutLoading(button, true);

        try {
            const response = await fetch(checkoutUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            if (data.url) {
                window.location.href = data.url;
                return;
            }
            window.alert('Error starting checkout: ' + (data.error || 'Unknown error'));
        } catch (error) {
            window.alert('Network error. Please try again.');
        }

        setCheckoutLoading(button, false);
    }

    function openLegalShieldModal(button) {
        const modal = document.getElementById('legal-shield-modal');
        if (!modal) {
            return;
        }
        modal.dataset.propertyId = button.dataset.propertyId;
        modal.querySelector('[data-modal-property-title]').textContent = button.dataset.propertyTitle || 'Selected property';
        modal.classList.remove('modal-hidden');
    }

    function closeLegalShieldModal() {
        const modal = document.getElementById('legal-shield-modal');
        if (modal) {
            modal.classList.add('modal-hidden');
        }
    }

    async function uploadDocument(input) {
        const modal = document.getElementById('legal-shield-modal');
        const result = document.getElementById('legal-shield-result');
        if (!modal || !result || !input.files.length || !modal.dataset.propertyId) {
            return;
        }

        const form = new FormData();
        form.append('document', input.files[0]);
        form.append('document_type', document.getElementById('legal-shield-document-type').value);

        result.classList.remove('hidden');
        result.innerHTML = '<div class="flex items-center gap-x-3 p-4 bg-white/5 rounded-2xl"><i class="fas fa-spinner fa-spin text-[#D4AF37]"></i><span>Processing with Legal Shield...</span></div>';

        try {
            const response = await fetch(`/properties/${modal.dataset.propertyId}/upload-document/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() },
                body: form
            });
            const data = await response.json();

            if (!data.success) {
                result.innerHTML = `<div class="text-red-400 p-4">Error: ${data.error || 'Upload failed.'}</div>`;
                return;
            }

            const extracted = data.extracted_data || {};
            result.innerHTML = `
                <div class="p-5 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl">
                    <div class="flex items-center gap-x-3 mb-3">
                        <i class="fas fa-check-circle text-emerald-400"></i>
                        <span class="font-semibold">Document linked and processed</span>
                    </div>
                    <div class="grid grid-cols-2 gap-x-4 text-sm">
                        <div><span class="text-white/50">Address:</span> <span class="font-medium">${extracted.detected_address || 'No data yet'}</span></div>
                        <div><span class="text-white/50">Size:</span> <span class="font-medium">${extracted.detected_size || 'No data yet'}</span></div>
                    </div>
                </div>
            `;
        } catch (error) {
            result.innerHTML = '<div class="text-red-400 p-4">Upload failed.</div>';
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-action="checkout"]').forEach(function (button) {
            button.addEventListener('click', startStripeCheckout);
        });
        document.querySelectorAll('[data-action="open-legal-shield"]').forEach(function (button) {
            button.addEventListener('click', function () {
                openLegalShieldModal(button);
            });
        });
        document.querySelectorAll('[data-action="close-legal-shield"]').forEach(function (button) {
            button.addEventListener('click', closeLegalShieldModal);
        });
        const documentInput = document.getElementById('legal-shield-file');
        if (documentInput) {
            documentInput.addEventListener('change', function () {
                uploadDocument(documentInput);
            });
        }
    });
})();

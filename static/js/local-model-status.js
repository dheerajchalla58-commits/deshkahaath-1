(() => {
    const banner = document.getElementById('localModelStatus');
    if (!banner) return;
    async function refresh() {
        try {
            const response = await fetch('/api/local-model-status', {cache: 'no-store'});
            if (!response.ok) return;
            const data = await response.json();
            if (data.state === 'disabled' || data.state === 'ready') {
                banner.hidden = true;
                return;
            }
            banner.textContent = data.message;
            banner.hidden = false;
            if (data.state !== 'error') setTimeout(refresh, 5000);
        } catch (_) {}
    }
    refresh();
})();

(() => {
    const key = 'desh_ke_haath_demo_cart';
    const read = () => { try { const items = JSON.parse(localStorage.getItem(key) || '[]'); return Array.isArray(items) ? items : []; } catch (_) { return []; } };
    const save = items => { localStorage.setItem(key, JSON.stringify(items)); window.dispatchEvent(new Event('desh-cart-changed')); };
    const count = () => {
        const badge = document.querySelector('.cart-count');
        if (!badge) return;
        const total = read().reduce((sum, item) => sum + (Number(item.qty) || 0), 0);
        badge.textContent = total;
        badge.hidden = total === 0;
    };
    const openCart = () => {
        let dialog = document.getElementById('demoCartDialog');
        if (!dialog) {
            dialog = document.createElement('dialog');
            dialog.id = 'demoCartDialog';
            dialog.className = 'demo-cart-dialog';
            document.body.append(dialog);
        }
        dialog.replaceChildren();
        const heading = document.createElement('h2'); heading.textContent = 'Your collection';
        const close = document.createElement('button'); close.type = 'button'; close.className = 'demo-cart-close'; close.setAttribute('aria-label', 'Close cart'); close.textContent = '×'; close.onclick = () => dialog.close();
        dialog.append(close, heading);
        const items = read();
        if (!items.length) {
            const empty = document.createElement('p'); empty.textContent = 'Your collection is empty.'; dialog.append(empty);
        } else {
            let total = 0;
            items.forEach((item, index) => {
                const row = document.createElement('div'); row.className = 'demo-cart-row';
                const info = document.createElement('span'); info.textContent = `${item.name} · ${item.qty} × ₹${Number(item.price || 0).toLocaleString('en-IN')}`;
                const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Remove'; remove.setAttribute('aria-label', `Remove ${item.name}`);
                remove.onclick = () => { const current = read(); current.splice(index, 1); save(current); openCart(); };
                total += Number(item.price || 0) * Number(item.qty || 0);
                row.append(info, remove); dialog.append(row);
            });
            const summary = document.createElement('p'); summary.className = 'demo-cart-total'; summary.textContent = `Total: ₹${total.toLocaleString('en-IN')}`; dialog.append(summary);
            const note = document.createElement('p'); note.textContent = 'Demo collection. Checkout is not connected.'; dialog.append(note);
        }
        if (!dialog.open) dialog.showModal();
    };
    document.addEventListener('DOMContentLoaded', () => {
        count();
        document.querySelector('.cart-btn')?.addEventListener('click', openCart);
        const quantity = document.getElementById('pdpQty');
        document.getElementById('qtyMinus')?.addEventListener('click', () => { quantity.value = Math.max(1, Number(quantity.value) - 1); });
        document.getElementById('qtyPlus')?.addEventListener('click', () => { quantity.value = Math.min(10, Number(quantity.value) + 1); });
        document.querySelector('.btn-pdp-add-minimal')?.addEventListener('click', () => {
            const product = document.querySelector('.product-detail-section').dataset;
            const items = read(), existing = items.find(item => item.id === product.productId), qty = Number(quantity.value) || 1;
            if (existing) existing.qty = Number(existing.qty) + qty;
            else items.push({id: product.productId, name: product.productName, state: product.productState, price: Number(product.productPrice), image: product.productImage, qty});
            save(items);
            document.querySelector('.pdp-cart-status').textContent = 'Added to your collection.';
        });
    });
    window.addEventListener('desh-cart-changed', count);
    window.addEventListener('storage', count);
})();

(function () {
  const CART_KEY    = 'urbanwear_cart';
  const SUMMARY_KEY = 'urbanwear_cart_summary';

  /* ─── helpers ─────────────────────────────────── */
  function getCart() {
    try {
      const s = localStorage.getItem(CART_KEY);
      return s ? JSON.parse(s) : [];
    } catch (e) { return []; }
  }

  function fmt(n) {
    return '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 0 });
  }

  function effectivePrice(item) {
    const disc = parseFloat(item.discount_percentage) || 0;
    return disc > 0 ? item.price * (1 - disc / 100) : item.price;
  }

  function updateCartBadge() {
    const cart = getCart();
    const total = cart.reduce((s, i) => s + (parseInt(i.qty) || 1), 0);
    document.querySelectorAll('.cart-count-badge').forEach(b => {
      b.innerText = total;
      b.style.display = total > 0 ? 'flex' : 'none';
    });
  }

  function saveCartLocally(item) {
    const cart = getCart();
    const ex   = cart.find(i => String(i.id) === String(item.id));
    if (ex) {
      ex.qty = (parseInt(ex.qty) || 1) + (parseInt(item.qty) || 1);
    } else {
      cart.push({
        id:                  item.id,
        name:                item.name || '',
        price:               parseFloat(item.price) || 0,
        img:                 item.img  || '',
        qty:                 parseInt(item.qty) || 1,
        discount_percentage: parseFloat(item.discount_percentage || 0),
        size:                item.size || ''
      });
    }
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
    updateCartBadge();
    dispatchCartUpdate();
    return cart;
  }

  function dispatchCartUpdate() {
    window.dispatchEvent(new CustomEvent('cartUpdated'));
  }

  /* ─── mini-cart DOM ──────────────────────────── */
  function ensureMiniCartDOM() {
    if (document.getElementById('mini-cart-panel')) return;

    // Inject CSS if not already linked
    if (!document.querySelector('link[href*="mini-cart.css"]')) {
      const link = document.createElement('link');
      link.rel  = 'stylesheet';
      link.href = 'css/mini-cart.css';
      document.head.appendChild(link);
    }

    const overlay = document.createElement('div');
    overlay.id = 'mini-cart-overlay';
    overlay.onclick = () => toggleMiniCart(false);

    const panel = document.createElement('div');
    panel.id = 'mini-cart-panel';
    panel.innerHTML = `
      <div class="mini-cart-header">
        <div class="mc-header-left">
          <span class="mc-bag-icon"><i class="fa-solid fa-bag-shopping"></i></span>
          <h3>Shopping Bag</h3>
          <span class="mc-count-pill" id="mc-count-pill">0</span>
        </div>
        <button class="close-mini-cart" onclick="toggleMiniCart(false)" aria-label="Close cart">&#xd7;</button>
      </div>
      <div id="mini-cart-items"></div>
      <div class="mini-cart-footer" id="mini-cart-footer" style="display:none;">
        <div class="mini-cart-total">
          <span>Subtotal</span>
          <span id="mini-cart-subtotal">₹0</span>
        </div>
        <p class="mini-cart-tax-info">Shipping &amp; taxes calculated at checkout.</p>
        <button class="btn-checkout-mini" onclick="window.location.href='checkout.html'">Proceed to Checkout</button>
        <a href="cart.html" class="view-full-cart">View Full Bag</a>
      </div>`;

    document.body.appendChild(overlay);
    document.body.appendChild(panel);
  }

  window.toggleMiniCart = function (open) {
    ensureMiniCartDOM();
    const panel   = document.getElementById('mini-cart-panel');
    const overlay = document.getElementById('mini-cart-overlay');
    if (open === undefined) open = !panel.classList.contains('active');

    if (open) {
      renderMiniCart();
      overlay.style.display = 'block';
      // tiny delay so display:block kicks in before the transition
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          overlay.style.opacity = '1';
          panel.classList.add('active');
        });
      });
      document.body.style.overflow = 'hidden';
    } else {
      overlay.style.opacity = '0';
      panel.classList.remove('active');
      setTimeout(() => { overlay.style.display = 'none'; }, 500);
      document.body.style.overflow = '';
    }
  };

  window.renderMiniCart = function () {
    ensureMiniCartDOM();
    const cart    = getCart();
    const itemsEl = document.getElementById('mini-cart-items');
    const footerEl= document.getElementById('mini-cart-footer');
    const countEl = document.getElementById('mc-count-pill');
    if (!itemsEl) return;

    const totalQty = cart.reduce((s, i) => s + (parseInt(i.qty) || 1), 0);
    if (countEl) countEl.textContent = totalQty;

    if (cart.length === 0) {
      itemsEl.innerHTML = `
        <div class="empty-mini-cart">
          <div class="mc-empty-icon"><i class="fa-regular fa-bag-shopping"></i></div>
          <div class="mc-empty-title">Your bag is empty</div>
          <div class="mc-empty-sub">Add something you love.</div>
          <a href="men.html" class="mc-shop-btn">Start Shopping</a>
        </div>`;
      if (footerEl) footerEl.style.display = 'none';
      return;
    }

    let html     = '';
    let subtotal = 0;

    cart.forEach(item => {
      const ep  = effectivePrice(item);
      const qty = parseInt(item.qty) || 1;
      subtotal += ep * qty;
      const disc = parseFloat(item.discount_percentage) || 0;

      const imgSrc = item.img || 'https://via.placeholder.com/90x120?text=Item';

      html += `
        <div class="mini-cart-item" data-id="${item.id}">
          <a href="product.html?id=${item.id}" class="mc-item-img-link">
            <img src="${imgSrc}" alt="${item.name}" loading="lazy">
          </a>
          <div class="mc-item-info">
            <a href="product.html?id=${item.id}" class="mc-item-name">${item.name}</a>
            <div class="mc-item-price-row">
              <span class="mc-item-ep">${fmt(ep)}</span>
              ${disc > 0 ? `<span class="mc-item-orig">${fmt(item.price)}</span><span class="mc-item-disc">-${disc}%</span>` : ''}
            </div>
            <div class="mc-bottom-row">
              <div class="mc-qty-ctrl">
                <button class="mc-qty-btn" onclick="mcChangeQty('${item.id}', -1)" aria-label="Decrease">−</button>
                <span class="mc-qty-val">${qty}</span>
                <button class="mc-qty-btn" onclick="mcChangeQty('${item.id}', 1)" aria-label="Increase">+</button>
              </div>
              <button class="mc-remove" onclick="mcRemoveItem('${item.id}')" aria-label="Remove item">Remove</button>
            </div>
          </div>
        </div>`;
    });

    itemsEl.innerHTML = html;

    const subEl = document.getElementById('mini-cart-subtotal');
    if (subEl) subEl.textContent = fmt(subtotal);
    if (footerEl) footerEl.style.display = '';
  };

  /* ─── quantity & remove (local-first) ──────── */
  window.mcChangeQty = function (id, delta) {
    const cart = getCart();
    const item = cart.find(i => String(i.id) === String(id));
    if (!item) return;
    const newQty = (parseInt(item.qty) || 1) + delta;
    if (newQty < 1) { mcRemoveItem(id); return; }
    item.qty = newQty;
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
    updateCartBadge();
    dispatchCartUpdate();
    renderMiniCart();

    // Sync with backend if logged in
    if (window.IS_LOGGED_IN && window.AUTH_TOKEN && window.API) {
      const root = window.API.baseUrl;
      fetch(`${root}/api/v1/cart/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${window.AUTH_TOKEN}` },
        body: JSON.stringify({ quantity: newQty })
      }).catch(() => {});
    }
  };

  window.mcRemoveItem = function (id) {
    let cart = getCart();
    cart = cart.filter(i => String(i.id) !== String(id));
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
    updateCartBadge();
    dispatchCartUpdate();
    renderMiniCart();

    if (window.IS_LOGGED_IN && window.AUTH_TOKEN && window.API) {
      const root = window.API.baseUrl;
      fetch(`${root}/api/v1/cart/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${window.AUTH_TOKEN}` }
      }).catch(() => {});
    }
  };

  /* ─── legacy aliases (cart.php uses these) ── */
  window.changeMiniCartQty  = window.mcChangeQty;
  window.removeMiniCartItem = window.mcRemoveItem;

  /* ─── main addToCart ─────────────────────── */
  window.addToCart = function (id, name, price, img, qty, discount_percentage, size) {
    if (!id) return;
    const item = {
      id:                  String(id),
      name:                name  || '',
      price:               parseFloat(price) || 0,
      img:                 img   || '',
      qty:                 Math.max(1, parseInt(qty) || 1),
      discount_percentage: parseFloat(discount_percentage || 0),
      size:                size || ''
    };

    saveCartLocally(item);

    // Backend sync (fire & forget)
    if (window.IS_LOGGED_IN && window.AUTH_TOKEN && window.API) {
      const root = window.API.baseUrl;
      fetch(`${root}/api/v1/cart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${window.AUTH_TOKEN}` },
        body: JSON.stringify({ productId: item.id, quantity: item.qty, size: item.size })
      }).catch(() => {});
    }

    // Open mini-cart sidebar (instead of redirecting)
    toggleMiniCart(true);
  };

  /* ─── backend refresh (used by cart.php) ─── */
  window.refreshCartFromBackend = async function () {
    if (!window.IS_LOGGED_IN || !window.AUTH_TOKEN || !window.API) return null;
    const root = window.API.baseUrl;
    try {
      const res  = await fetch(`${root}/api/v1/cart`, {
        headers: { 'Authorization': `Bearer ${window.AUTH_TOKEN}` }
      });
      const data = await res.json();
      if (data.success && data.data) {
        const b     = data.data;
        const items = b.items || [];
        const local = items.map(item => {
          let pid = item.productId;
          if (pid && typeof pid === 'object') pid = pid._id || pid.id;
          const rawImg = item.imageUrl || '';
          const img    = (rawImg.startsWith('http') || rawImg.startsWith('//') || !rawImg)
            ? rawImg : (root + (rawImg.startsWith('/') ? '' : '/') + rawImg);
          return {
            id:                  String(pid),
            cartItemId:          item._id,
            name:                item.productName || 'Product',
            price:               parseFloat(item.price) || 0,
            img,
            qty:                 parseInt(item.quantity) || 1,
            discount_percentage: parseFloat(item.discount_percentage || 0),
            size:                item.size,
            color:               item.color
          };
        });
        localStorage.setItem(CART_KEY, JSON.stringify(local));
        localStorage.setItem(SUMMARY_KEY, JSON.stringify(b.summary || {}));
        updateCartBadge();
        dispatchCartUpdate();
        if (typeof renderCart    === 'function') renderCart();
        if (typeof renderSummary === 'function') renderSummary();
        return b;
      }
      return null;
    } catch (e) { return null; }
  };

  /* ─── init ───────────────────────────────── */
  function init() {
    updateCartBadge();
    if (window.IS_LOGGED_IN) window.refreshCartFromBackend();

    // Delegated handler for .add-to-cart-btn on PLP pages
    document.body.addEventListener('click', e => {
      const btn = e.target.closest('.add-to-cart-btn');
      if (btn) {
        e.preventDefault();
        const d    = btn.dataset;
        const disc = d.discountPercentage ? parseFloat(d.discountPercentage) : 0;
        if (d.id) window.addToCart(d.id, d.name, d.price, d.image, 1, disc);
      }

      // Cart icon click → open mini-cart (any element with data-open-cart)
      const cartTrigger = e.target.closest('[data-open-cart]');
      if (cartTrigger) {
        e.preventDefault();
        toggleMiniCart(true);
      }
    });

    // Close on ESC
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') toggleMiniCart(false);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();

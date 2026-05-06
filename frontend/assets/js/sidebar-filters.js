/**
 * URBANWEAR — Sidebar Filter Controller
 * Handles Size, Price, and Discount filters on PLP pages.
 * Syncs with URL query params for server-side PHP filtering.
 */
(function() {
    const metaCategory = document.querySelector('meta[name="category"]');
    const category = metaCategory ? metaCategory.getAttribute('content') : 'men';

    // Elements
    const sizeBtns = document.querySelectorAll('.sf-size-btn');
    const priceApplyBtn = document.getElementById('sf-price-apply');
    const minPriceInput = document.getElementById('sf-min-price');
    const maxPriceInput = document.getElementById('sf-max-price');
    const discountRadios = document.querySelectorAll('input[name="discount"]');
    const clearAllBtn = document.getElementById('sf-clear-all');

    /**
     * Get current filters from UI
     */
    function getActiveFilters() {
        const activeSizeBtn = document.querySelector('.sf-size-btn.active');
        const activeDiscountRadio = document.querySelector('input[name="discount"]:checked');

        return {
            category: category,
            size: activeSizeBtn ? activeSizeBtn.dataset.size : '',
            minPrice: minPriceInput.value || '',
            maxPrice: maxPriceInput.value || '',
            minDiscount: activeDiscountRadio ? activeDiscountRadio.value : ''
        };
    }

    /**
     * Redirect to update page results
     */
    function applyFilters() {
        const filters = getActiveFilters();
        const params = new URLSearchParams();

        if (filters.size) params.set('size', filters.size);
        if (filters.minPrice) params.set('minPrice', filters.minPrice);
        if (filters.maxPrice) params.set('maxPrice', filters.maxPrice);
        if (filters.minDiscount) params.set('minDiscount', filters.minDiscount);

        const queryString = params.toString();
        window.location.href = `${category}.php${queryString ? '?' + queryString : ''}`;
    }

    /**
     * Initialize UI from URL params
     */
    function initFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // Size
        const sizeParam = urlParams.get('size');
        if (sizeParam) {
            sizeBtns.forEach(btn => {
                if (btn.dataset.size === sizeParam) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
        }

        // Price
        const minPriceParam = urlParams.get('minPrice');
        const maxPriceParam = urlParams.get('maxPrice');
        if (minPriceParam) minPriceInput.value = minPriceParam;
        if (maxPriceParam) maxPriceInput.value = maxPriceParam;

        // Discount
        const minDiscountParam = urlParams.get('minDiscount');
        if (minDiscountParam) {
            discountRadios.forEach(radio => {
                if (radio.value === minDiscountParam) {
                    radio.checked = true;
                }
            });
        }
    }

    // --- EVENT LISTENERS ---

    // Size clicks
    sizeBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const wasActive = btn.classList.contains('active');
            
            // Remove active from all
            sizeBtns.forEach(b => b.classList.remove('active'));
            
            // If it wasn't active, make it active (toggle behavior but only one at a time)
            if (!wasActive) {
                btn.classList.add('active');
            }
            
            applyFilters();
        });
    });

    // Price Apply click
    if (priceApplyBtn) {
        priceApplyBtn.addEventListener('click', (e) => {
            e.preventDefault();
            applyFilters();
        });
    }

    // Discount radio change
    discountRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            applyFilters();
        });
    });

    // Clear All
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = `${category}.php`;
        });
    }

    // Start
    initFromURL();

})();

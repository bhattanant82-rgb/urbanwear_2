/**
 * Premium Search Autocomplete
 */
document.addEventListener('DOMContentLoaded', () => {
    const searchWrapper = document.getElementById('searchWrapper');
    const searchInput = document.getElementById('searchInput');
    const searchIconBtn = document.getElementById('searchIconBtn');
    const searchResults = document.getElementById('searchResults');
    let debounceTimer;

    if (!searchWrapper || !searchInput || !searchIconBtn) return;

    // Toggle Expand
    searchIconBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        searchWrapper.classList.toggle('expanded');
        if (searchWrapper.classList.contains('expanded')) {
            searchInput.focus();
        } else {
            searchInput.value = '';
            searchResults.classList.remove('show');
        }
    });

    // Handle Input
    searchInput.addEventListener('input', () => {
        const query = searchInput.value.trim();
        clearTimeout(debounceTimer);

        if (query.length < 2) {
            searchResults.classList.remove('show');
            return;
        }

        debounceTimer = setTimeout(() => {
            fetchSearchResults(query);
        }, 300);
    });

    // Close on click outside
    document.addEventListener('click', (e) => {
        if (!searchWrapper.contains(e.target)) {
            searchWrapper.classList.remove('expanded');
            searchResults.classList.remove('show');
            searchInput.value = '';
        }
    });

    async function fetchSearchResults(query) {
        try {
            const root = window.API ? window.API.baseUrl : 'http://127.0.0.1:5000';
            const response = await fetch(`${root}/api/v1/products/search/autocomplete?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (data.success) {
                renderResults(data.data);
            }
        } catch (error) {
            console.error('Search error:', error);
        }
    }

    function renderResults(products) {
        searchResults.innerHTML = '';

        if (!products || products.length === 0) {
            searchResults.innerHTML = '<div class="no-results">No products found</div>';
        } else {
            products.forEach(p => {
                const rawImg = (Array.isArray(p.images) && p.images.length) ? p.images[0] : (p.image || '');
                const img = window.API ? window.API.getImageUrl(rawImg) : (rawImg || 'https://via.placeholder.com/100');
                const item = document.createElement('a');
                item.href = `product.html?id=${p._id || p.id}`;
                item.className = 'search-result-item';
                item.innerHTML = `
                    <div class="search-result-thumb">
                        <img src="${img}" alt="${p.title}">
                    </div>
                    <div class="search-result-info">
                        <div class="search-result-name">${p.title}</div>
                        <div class="search-result-price">₹${p.price.toLocaleString()}</div>
                    </div>
                `;
                searchResults.appendChild(item);
            });
        }

        searchResults.classList.add('show');
    }
});

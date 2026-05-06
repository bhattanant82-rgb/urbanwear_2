/**
 * Category Analytics - Real-time product filtering with Chart.js visualization
 * Implements lazy loading and caching for optimal performance
 */

(function () {
    'use strict';

    // Get category from page
    const categoryMeta = document.querySelector('meta[name="category"]');
    const CATEGORY = categoryMeta ? categoryMeta.content : 'men';
    const API_BASE = window.API ? window.API.baseUrl + '/api/v1' : 'http://127.0.0.1:5000/api/v1';

    // Cache for analytics data
    const analyticsCache = {
        bestsellers: null,
        trending: null,
        timeless: null
    };

    // Store original products for "All Products" filter
    let allProducts = [];
    let currentChart = null;

    // Premium color palette for charts
    const CHART_COLORS = [
        '#2C3E50', // Dark blue-grey
        '#34495E', // Medium grey
        '#7F8C8D', // Light grey
        '#95A5A6', // Silver
        '#BDC3C7'  // Light silver
    ];

    /**
     * Initialize analytics on page load
     */
    function init() {
        // Store all products from the grid
        const productCards = document.querySelectorAll('.product-card');
        allProducts = Array.from(productCards);

        // Attach filter button listeners
        const filterButtons = document.querySelectorAll('.filter-btn');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', handleFilterClick);
        });

        console.log('✅ Category Analytics initialized for:', CATEGORY);
    }

    /**
     * Handle filter button click
     */
    async function handleFilterClick(e) {
        const button = e.currentTarget;
        const filter = button.dataset.filter;

        // Update active state
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');

        // Handle "All Products" - no API call needed
        if (filter === 'all') {
            showAllProducts();
            hideChart();
            return;
        }

        // Check cache first (lazy loading optimization)
        if (analyticsCache[filter]) {
            console.log(`📦 Using cached data for ${filter}`);
            renderAnalytics(analyticsCache[filter], filter);
            return;
        }

        // Fetch analytics data
        await fetchAndRenderAnalytics(filter);
    }

    /**
     * Fetch analytics data from API and render
     */
    async function fetchAndRenderAnalytics(filter) {
        const loadingSpinner = showLoadingSpinner();

        try {
            // STRICT URL REQUIREMENT
            const endpoint = `${API_BASE}/products/analytics/${filter}/?category=${CATEGORY}`;
            console.log(`🔄 Fetching ${filter} data from:`, endpoint);

            const response = await fetch(endpoint);
            const result = await response.json();

            hideLoadingSpinner(loadingSpinner);

            if (result.success !== true) {
                console.error('API Error:', result.message);
                showError('Failed to load analytics data');
                return;
            }

            // Cache and render
            analyticsCache[filter] = result;
            renderAnalytics(result, filter);

        } catch (error) {
            console.error('❌ Error fetching analytics:', error);
            hideLoadingSpinner(loadingSpinner);
            showError('Network error. Please try again.');
        }
    }

    /**
     * Render analytics: filter products and show chart
     */
    function renderAnalytics(result, filter) {
        const { data } = result;

        if (!data || data.length === 0) {
            showInsufficientDataMessage('No enough data available yet.');
            return;
        }

        // Filter product grid
        filterProductGrid(data);

        // Render donut chart
        renderDonutChart(data, filter);

        // Show chart container
        document.getElementById('analyticsChart').style.display = 'flex';
    }

    /**
     * Filter product grid to show only specified products
     */
    function filterProductGrid(analyticsData) {
        const productIds = analyticsData.map(item => item.productId.toString());

        allProducts.forEach(card => {
            const cardLink = card.closest('.product-card-link');
            const productId = extractProductId(cardLink);

            if (productIds.includes(productId)) {
                cardLink.style.display = 'block';
            } else {
                cardLink.style.display = 'none';
            }
        });
    }

    /**
     * Extract product ID from product card link
     */
    function extractProductId(cardLink) {
        const href = cardLink.getAttribute('href');
        const match = href.match(/id=([a-f0-9]+)/);
        return match ? match[1] : '';
    }

    /**
     * Render donut chart using Chart.js
     */
    function renderDonutChart(data, filterType) {
        const canvas = document.getElementById('donutChart');
        const ctx = canvas.getContext('2d');

        if (currentChart) {
            currentChart.destroy();
        }

        // Use real values from API (name, totalSales)
        const labels = data.map(item => item.name);
        const values = data.map(item => item.totalSales || item.trendingScore || item.avgRating);
        const colors = CHART_COLORS.slice(0, data.length);

        currentChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.label}: ${context.raw}`;
                            }
                        }
                    }
                }
            }
        });

        renderChartLegend(data, colors);
    }

    /**
     * Render custom chart legend
     */
    function renderChartLegend(data, colors) {
        const legendContainer = document.getElementById('chartLegend');
        legendContainer.innerHTML = '';

        data.forEach((item, index) => {
            const legendItem = document.createElement('div');
            legendItem.className = 'legend-item';
            const value = item.totalSales || item.avgRating || item.trendingScore;
            legendItem.innerHTML = `
                <span class="legend-color" style="background-color: ${colors[index]}"></span>
                <span class="legend-label">${item.name}</span>
                <span class="legend-value">${value}</span>
            `;
            legendContainer.appendChild(legendItem);
        });
    }

    /**
     * Show all products (reset filter)
     */
    function showAllProducts() {
        allProducts.forEach(card => {
            const cardLink = card.closest('.product-card-link');
            cardLink.style.display = 'block';
        });
    }

    /**
     * Hide chart container
     */
    function hideChart() {
        document.getElementById('analyticsChart').style.display = 'none';
        if (currentChart) {
            currentChart.destroy();
            currentChart = null;
        }
    }

    /**
     * Show insufficient data message
     */
    function showInsufficientDataMessage(message) {
        const chartContainer = document.getElementById('analyticsChart');
        chartContainer.style.display = 'flex';
        chartContainer.innerHTML = `
      <div class="insufficient-data-message">
        <i class="fa-solid fa-chart-pie"></i>
        <p>${message}</p>
        <small>Check back after more orders and reviews!</small>
      </div>
    `;
    }

    /**
     * Show error message
     */
    function showError(message) {
        const chartContainer = document.getElementById('analyticsChart');
        chartContainer.style.display = 'flex';
        chartContainer.innerHTML = `
      <div class="error-message">
        <i class="fa-solid fa-exclamation-triangle"></i>
        <p>${message}</p>
      </div>
    `;
    }

    /**
     * Show loading spinner
     */
    function showLoadingSpinner() {
        const spinner = document.createElement('div');
        spinner.className = 'analytics-spinner';
        spinner.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading analytics...';
        document.querySelector('.analytics-section').appendChild(spinner);
        return spinner;
    }

    /**
     * Hide loading spinner
     */
    function hideLoadingSpinner(spinner) {
        if (spinner && spinner.parentNode) {
            spinner.parentNode.removeChild(spinner);
        }
    }

    /**
     * Truncate text to specified length
     */
    function truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();

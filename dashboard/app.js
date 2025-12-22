// Rise Local Lead Discovery Dashboard
// SECURITY: Credentials are now fetched from secure backend API
// No hardcoded API keys - implements secure authentication

// Default franchise blocklist
const DEFAULT_FRANCHISES = [
    'Mr. Electric',
    'Mister Sparky',
    'Mr. Sparky',
    'Benjamin Franklin Electric',
    'Service Experts',
    'ARS Rescue',
    'ARS/Rescue Rooter',
    'One Hour',
    'Neighborly'
];

// Initialize Supabase client
let supabase;

// Map instance
let map;
let searchCircle;
let searchMarker;
let leadMarkers = [];

// Metro area center coordinates
const METRO_CENTERS = {
    'Austin': { lat: 30.2672, lng: -97.7431 },
    'Dallas-Fort Worth': { lat: 32.7767, lng: -96.7970 }
};

// App State
const state = {
    metroAreas: [],
    franchiseList: [...DEFAULT_FRANCHISES],
    filters: {
        enableRating: false,
        minRating: 0,
        maxRating: 5,
        enableReviews: false,
        minReviews: 0,
        maxReviews: 9999
    }
};

// DOM Elements
const elements = {
    // Stats
    totalLeads: document.getElementById('total-leads'),
    leadsToday: document.getElementById('leads-today'),
    jobsRunning: document.getElementById('jobs-running'),
    totalCost: document.getElementById('total-cost'),

    // Discovery
    metroSelect: document.getElementById('metro-select'),
    zipCode: document.getElementById('zip-code'),
    radius: document.getElementById('radius'),
    runDiscovery: document.getElementById('run-discovery'),
    discoveryStatus: document.getElementById('discovery-status'),
    statusText: document.getElementById('status-text'),
    statusDetails: document.getElementById('status-details'),

    // Filters
    franchiseList: document.getElementById('franchise-list'),
    newFranchise: document.getElementById('new-franchise'),
    addFranchise: document.getElementById('add-franchise'),
    saveFilters: document.getElementById('save-filters'),
    enableRatingFilter: document.getElementById('enable-rating-filter'),
    ratingFilterOptions: document.getElementById('rating-filter-options'),
    enableReviewFilter: document.getElementById('enable-review-filter'),
    reviewFilterOptions: document.getElementById('review-filter-options'),
    minRating: document.getElementById('min-rating'),
    maxRating: document.getElementById('max-rating'),
    minReviews: document.getElementById('min-reviews'),
    maxReviews: document.getElementById('max-reviews'),

    // Tables
    jobsTable: document.getElementById('jobs-table'),
    refreshJobs: document.getElementById('refresh-jobs'),
    metroStats: document.getElementById('metro-stats'),

    // Modal
    configModal: document.getElementById('config-modal'),
    configUrl: document.getElementById('config-url'),
    configKey: document.getElementById('config-key'),
    saveConfig: document.getElementById('save-config'),

    // Toast
    toastContainer: document.getElementById('toast-container')
};

// Initialize App
async function init() {
    // Check if Supabase library loaded
    if (!window.supabase) {
        console.error('Supabase library not loaded!');
        showToast('Error: Supabase library failed to load', 'error');
        return;
    }

    // Initialize auth manager with secure credentials
    try {
        const isAuthenticated = await window.authManager.init();

        if (!isAuthenticated) {
            // Redirect to login if not authenticated
            window.location.href = 'login.html';
            return;
        }

        // Get authenticated Supabase client
        supabase = window.authManager.getClient();
        console.log('Supabase client initialized with secure auth');

        // Display logged-in user info
        const user = window.authManager.getCurrentUser();
        console.log('Logged in as:', user.email);

        // Update UI with user email
        const userEmailElement = document.getElementById('user-email');
        if (userEmailElement) {
            userEmailElement.textContent = user.email;
        }

    } catch (error) {
        console.error('Authentication failed:', error);
        showToast('Authentication error - redirecting to login', 'error');
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 2000);
        return;
    }

    // Load saved franchise list from localStorage
    const savedFranchises = localStorage.getItem('franchiseList');
    if (savedFranchises) {
        state.franchiseList = JSON.parse(savedFranchises);
    }

    // Load saved filters
    const savedFilters = localStorage.getItem('filters');
    if (savedFilters) {
        state.filters = JSON.parse(savedFilters);
        applyFilterState();
    }

    // Setup event listeners
    setupEventListeners();

    // Initialize map
    initMap();

    // Load initial data with individual error handling
    const loadResults = await Promise.allSettled([
        loadMetroAreas(),
        loadStats(),
        loadRecentJobs(),
        loadMetroStats(),
        loadLeadsOnMap()
    ]);

    // Check for any failures
    const failures = loadResults.filter(r => r.status === 'rejected');
    if (failures.length > 0) {
        console.error('Some data failed to load:', failures);
        showToast('Some data failed to load - check browser console (F12)', 'error');
    } else {
        showToast('Dashboard loaded successfully', 'success');
    }

    // Render franchise list
    renderFranchiseList();
}

// Event Listeners
function setupEventListeners() {
    // Logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            const result = await window.authManager.signOut();
            if (result.success) {
                window.location.href = 'login.html';
            } else {
                showToast('Logout failed: ' + result.error, 'error');
            }
        });
    }

    // Discovery
    elements.runDiscovery.addEventListener('click', runDiscovery);
    elements.refreshJobs.addEventListener('click', loadRecentJobs);

    // Franchise management
    elements.addFranchise.addEventListener('click', addFranchise);
    elements.newFranchise.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addFranchise();
    });

    // Filter toggles
    elements.enableRatingFilter.addEventListener('change', (e) => {
        state.filters.enableRating = e.target.checked;
        elements.ratingFilterOptions.classList.toggle('hidden', !e.target.checked);
    });

    elements.enableReviewFilter.addEventListener('change', (e) => {
        state.filters.enableReviews = e.target.checked;
        elements.reviewFilterOptions.classList.toggle('hidden', !e.target.checked);
    });

    // Save filters
    elements.saveFilters.addEventListener('click', saveFilters);

    // Map updates on metro/zip change
    elements.metroSelect.addEventListener('change', updateMapView);
    elements.zipCode.addEventListener('input', debounce(updateSearchArea, 500));
    elements.radius.addEventListener('input', debounce(updateSearchArea, 300));

    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadStats();
        loadRecentJobs();
    }, 30000);
}

// Debounce helper
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Load Metro Areas
async function loadMetroAreas() {
    try {
        const { data, error } = await supabase
            .from('metro_areas')
            .select('*')
            .eq('is_active', true)
            .order('name');

        if (error) throw error;

        state.metroAreas = data;

        // Populate select
        elements.metroSelect.innerHTML = '<option value="">Select metro area...</option>';
        data.forEach(metro => {
            const option = document.createElement('option');
            option.value = metro.id;
            option.textContent = metro.name;
            elements.metroSelect.appendChild(option);
        });
    } catch (err) {
        console.error('Error loading metro areas:', err);
        showToast('Failed to load metro areas', 'error');
    }
}

// Load Stats
async function loadStats() {
    try {
        // Total leads
        const { count: totalLeads } = await supabase
            .from('leads')
            .select('*', { count: 'exact', head: true });

        elements.totalLeads.textContent = totalLeads?.toLocaleString() || '0';

        // Leads today
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const { count: leadsToday } = await supabase
            .from('leads')
            .select('*', { count: 'exact', head: true })
            .gte('discovered_at', today.toISOString());

        elements.leadsToday.textContent = leadsToday?.toLocaleString() || '0';

        // Running jobs
        const { count: runningJobs } = await supabase
            .from('discovery_jobs')
            .select('*', { count: 'exact', head: true })
            .eq('status', 'running');

        elements.jobsRunning.textContent = runningJobs || '0';

        // Total API cost
        const { data: costData } = await supabase
            .from('discovery_jobs')
            .select('estimated_cost_cents');

        const totalCents = costData?.reduce((sum, job) => sum + (job.estimated_cost_cents || 0), 0) || 0;
        elements.totalCost.textContent = '$' + (totalCents / 100).toFixed(2);

    } catch (err) {
        console.error('Error loading stats:', err);
    }
}

// Load Recent Jobs
async function loadRecentJobs() {
    try {
        // Add timeout to prevent hanging
        const timeoutPromise = new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Request timed out - browser may be blocking Supabase')), 10000)
        );

        const queryPromise = supabase
            .from('discovery_jobs')
            .select(`
                *,
                search_configs (
                    metro_area_id,
                    metro_areas (name)
                )
            `)
            .order('created_at', { ascending: false })
            .limit(10);

        const { data, error } = await Promise.race([queryPromise, timeoutPromise]);

        if (error) throw error;

        if (!data || data.length === 0) {
            elements.jobsTable.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-state">No discovery jobs yet. Run your first discovery above!</td>
                </tr>
            `;
            return;
        }

        elements.jobsTable.innerHTML = data.map(job => {
            const date = new Date(job.created_at).toLocaleString();
            const metro = job.search_configs?.metro_areas?.name || 'Unknown';
            const statusClass = job.status === 'completed' ? 'completed' :
                               job.status === 'running' ? 'running' : 'failed';
            const cost = job.estimated_cost_cents ? '$' + (job.estimated_cost_cents / 100).toFixed(2) : '--';

            return `
                <tr>
                    <td>${date}</td>
                    <td>${metro}</td>
                    <td><span class="status-badge ${statusClass}">${job.status}</span></td>
                    <td>${job.places_found || 0}</td>
                    <td><strong>${job.leads_created || 0}</strong></td>
                    <td>${job.leads_filtered || 0}</td>
                    <td>${job.duplicates_skipped || 0}</td>
                    <td>${cost}</td>
                </tr>
            `;
        }).join('');

    } catch (err) {
        console.error('Error loading jobs:', err);
        elements.jobsTable.innerHTML = `
            <tr>
                <td colspan="8" class="empty-state" style="color: var(--neon-magenta);">
                    Failed to load data. If using Edge, go to Settings > Privacy > Tracking Prevention
                    and add "supabase.co" to the Allowed list, or try Chrome/Firefox.
                </td>
            </tr>
        `;
        showToast('Failed to load - check browser tracking settings', 'error');
    }
}

// Load Metro Stats
async function loadMetroStats() {
    try {
        // Fetch metro areas with lead counts directly
        const { data: metros, error } = await supabase
            .from('metro_areas')
            .select('id, name')
            .eq('is_active', true)
            .order('name');

        if (error) throw error;

        if (!metros || metros.length === 0) {
            elements.metroStats.innerHTML = '<div class="empty-state">No metro areas configured</div>';
            return;
        }

        // Get counts for each metro area
        const statsHtml = await Promise.all(metros.map(async (metro) => {
            const { count } = await supabase
                .from('leads')
                .select('*', { count: 'exact', head: true })
                .eq('metro_area_id', metro.id);

            return `
                <div class="metro-card">
                    <div>
                        <div class="metro-name">${metro.name}</div>
                        <div class="metro-label">Total Leads</div>
                    </div>
                    <div class="metro-count">${(count || 0).toLocaleString()}</div>
                </div>
            `;
        }));

        elements.metroStats.innerHTML = statsHtml.join('');

    } catch (err) {
        console.error('Error loading metro stats:', err);
        elements.metroStats.innerHTML = '<div class="empty-state" style="color: var(--neon-magenta);">Failed to load metro stats</div>';
    }
}

// Run Discovery
async function runDiscovery() {
    const metroId = elements.metroSelect.value;
    const zipCode = elements.zipCode.value.trim();
    const radius = parseInt(elements.radius.value) || 15;

    if (!metroId && !zipCode) {
        showToast('Please select a metro area or enter a zip code', 'error');
        return;
    }

    // Disable button
    elements.runDiscovery.disabled = true;
    elements.runDiscovery.innerHTML = `
        <svg class="spin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 11-6.219-8.56"/>
        </svg>
        Running...
    `;

    // Show status
    elements.discoveryStatus.classList.remove('hidden', 'success', 'error');
    elements.statusText.textContent = 'Starting discovery...';
    elements.statusDetails.innerHTML = '<p>Connecting to Google Places API...</p>';

    try {
        // Call edge function
        const response = await fetch(`${SUPABASE_URL}/functions/v1/discover-leads`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                metro_area_id: metroId || undefined,
                zip_code: zipCode || undefined,
                radius_miles: radius
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Discovery failed');
        }

        // Show success
        elements.discoveryStatus.classList.add('success');
        elements.statusText.textContent = 'Discovery completed!';
        elements.statusDetails.innerHTML = `
            <p><strong>Job ID:</strong> ${result.job_id}</p>
            <p><strong>Zip Codes Searched:</strong> ${result.stats.zip_codes_searched}</p>
            <p><strong>Places Found:</strong> ${result.stats.places_found}</p>
            <p><strong>Leads Created:</strong> ${result.stats.leads_created}</p>
            <p><strong>Filtered Out:</strong> ${result.stats.leads_filtered}</p>
            <p><strong>Duplicates:</strong> ${result.stats.duplicates_skipped}</p>
            <p><strong>Est. Cost:</strong> $${(result.stats.estimated_cost_cents / 100).toFixed(2)}</p>
        `;

        showToast(`Created ${result.stats.leads_created} new leads!`, 'success');

        // Refresh data
        await Promise.all([
            loadStats(),
            loadRecentJobs(),
            loadMetroStats(),
            loadLeadsOnMap()
        ]);

    } catch (err) {
        console.error('Discovery error:', err);
        elements.discoveryStatus.classList.add('error');
        elements.statusText.textContent = 'Discovery failed';
        elements.statusDetails.innerHTML = `<p>${err.message}</p>`;
        showToast('Discovery failed: ' + err.message, 'error');
    } finally {
        // Re-enable button
        elements.runDiscovery.disabled = false;
        elements.runDiscovery.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            Start Discovery
        `;
    }
}

// Franchise List Management
function renderFranchiseList() {
    elements.franchiseList.innerHTML = state.franchiseList.map((franchise, index) => `
        <span class="tag">
            ${franchise}
            <button class="tag-remove" onclick="removeFranchise(${index})" title="Remove">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
        </span>
    `).join('');
}

function addFranchise() {
    const value = elements.newFranchise.value.trim();
    if (!value) return;

    if (state.franchiseList.includes(value)) {
        showToast('This franchise is already in the list', 'error');
        return;
    }

    state.franchiseList.push(value);
    localStorage.setItem('franchiseList', JSON.stringify(state.franchiseList));
    renderFranchiseList();
    elements.newFranchise.value = '';
    showToast(`Added "${value}" to blocklist`, 'success');
}

function removeFranchise(index) {
    const removed = state.franchiseList.splice(index, 1)[0];
    localStorage.setItem('franchiseList', JSON.stringify(state.franchiseList));
    renderFranchiseList();
    showToast(`Removed "${removed}" from blocklist`, 'info');
}

// Make removeFranchise available globally for onclick
window.removeFranchise = removeFranchise;

// Filter Management
function applyFilterState() {
    elements.enableRatingFilter.checked = state.filters.enableRating;
    elements.ratingFilterOptions.classList.toggle('hidden', !state.filters.enableRating);
    elements.minRating.value = state.filters.minRating;
    elements.maxRating.value = state.filters.maxRating;

    elements.enableReviewFilter.checked = state.filters.enableReviews;
    elements.reviewFilterOptions.classList.toggle('hidden', !state.filters.enableReviews);
    elements.minReviews.value = state.filters.minReviews;
    elements.maxReviews.value = state.filters.maxReviews;
}

function saveFilters() {
    state.filters = {
        enableRating: elements.enableRatingFilter.checked,
        minRating: parseFloat(elements.minRating.value) || 0,
        maxRating: parseFloat(elements.maxRating.value) || 5,
        enableReviews: elements.enableReviewFilter.checked,
        minReviews: parseInt(elements.minReviews.value) || 0,
        maxReviews: parseInt(elements.maxReviews.value) || 9999
    };

    localStorage.setItem('filters', JSON.stringify(state.filters));
    localStorage.setItem('franchiseList', JSON.stringify(state.franchiseList));

    showToast('Filter settings saved!', 'success');
}

// Toast Notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${type === 'success' ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>' :
              type === 'error' ? '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>' :
              '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'}
        </svg>
        <span>${message}</span>
    `;

    elements.toastContainer.appendChild(toast);

    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Add spin animation for loading
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .spin {
        animation: spin 1s linear infinite;
    }
`;
document.head.appendChild(style);

// ========================================
// MAP FUNCTIONS
// ========================================

// Initialize Leaflet map
function initMap() {
    // Center on Texas (between Austin and Dallas)
    map = L.map('coverage-map').setView([31.0, -97.5], 7);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
}

// Load all leads onto the map
async function loadLeadsOnMap() {
    try {
        // Clear existing markers
        leadMarkers.forEach(marker => map.removeLayer(marker));
        leadMarkers = [];

        // Fetch leads with coordinates
        const { data: leads, error } = await supabase
            .from('leads')
            .select('id, business_name, address_city, latitude, longitude, google_rating, google_review_count, metro_area_id')
            .not('latitude', 'is', null)
            .not('longitude', 'is', null);

        if (error) throw error;

        // Create custom icon
        const leadIcon = L.divIcon({
            className: 'lead-marker',
            iconSize: [12, 12],
            iconAnchor: [6, 6]
        });

        // Add markers for each lead
        leads.forEach(lead => {
            const marker = L.marker([lead.latitude, lead.longitude], { icon: leadIcon })
                .bindPopup(`
                    <div class="popup-title">${lead.business_name}</div>
                    <div class="popup-info">${lead.address_city || 'Unknown'}</div>
                    <div class="popup-rating">★ ${lead.google_rating || 'N/A'} (${lead.google_review_count || 0} reviews)</div>
                `);
            marker.addTo(map);
            leadMarkers.push(marker);
        });

        console.log(`Loaded ${leads.length} leads on map`);

    } catch (err) {
        console.error('Error loading leads on map:', err);
    }
}

// Update map view when metro area changes
async function updateMapView() {
    const metroId = elements.metroSelect.value;

    if (!metroId) {
        // Reset to Texas view
        map.setView([31.0, -97.5], 7);
        return;
    }

    // Find selected metro
    const metro = state.metroAreas.find(m => m.id === metroId);
    if (!metro) return;

    // Get center coordinates
    const center = METRO_CENTERS[metro.name];
    if (center) {
        map.setView([center.lat, center.lng], 10);
    }

    // Clear any existing search area
    if (searchCircle) {
        map.removeLayer(searchCircle);
        searchCircle = null;
    }
    if (searchMarker) {
        map.removeLayer(searchMarker);
        searchMarker = null;
    }
}

// Update search area circle when zip code is entered
async function updateSearchArea() {
    const zipCode = elements.zipCode.value.trim();
    const radiusMiles = parseInt(elements.radius.value) || 15;

    // Clear existing search area
    if (searchCircle) {
        map.removeLayer(searchCircle);
        searchCircle = null;
    }
    if (searchMarker) {
        map.removeLayer(searchMarker);
        searchMarker = null;
    }

    if (!zipCode || zipCode.length < 5) return;

    try {
        // Try to get zip code from database
        const { data: zipData, error } = await supabase
            .from('zip_code_grids')
            .select('latitude, longitude, city')
            .eq('zip_code', zipCode)
            .single();

        let lat, lng, city;

        if (zipData && zipData.latitude && zipData.longitude) {
            lat = zipData.latitude;
            lng = zipData.longitude;
            city = zipData.city;
        } else {
            // Use geocoding fallback for common Texas zips
            const zipCoords = await geocodeZip(zipCode);
            if (!zipCoords) return;
            lat = zipCoords.lat;
            lng = zipCoords.lng;
            city = zipCoords.city;
        }

        // Convert miles to meters
        const radiusMeters = radiusMiles * 1609.34;

        // Create search marker
        const searchIcon = L.divIcon({
            className: 'search-marker',
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });

        searchMarker = L.marker([lat, lng], { icon: searchIcon })
            .bindPopup(`<div class="popup-title">Search Center</div><div class="popup-info">${city || zipCode}</div><div class="popup-info">${radiusMiles} mile radius</div>`)
            .addTo(map);

        // Create radius circle
        searchCircle = L.circle([lat, lng], {
            radius: radiusMeters,
            color: '#3535de',
            fillColor: '#3535de',
            fillOpacity: 0.1,
            weight: 2
        }).addTo(map);

        // Fit map to show the circle
        map.fitBounds(searchCircle.getBounds(), { padding: [20, 20] });

    } catch (err) {
        console.error('Error updating search area:', err);
    }
}

// Simple geocoding for Texas zip codes
async function geocodeZip(zipCode) {
    // Common Texas zip code coordinates (fallback)
    const texasZips = {
        '76052': { lat: 32.9715, lng: -97.3478, city: 'Haslet' },
        '78626': { lat: 30.6333, lng: -97.6780, city: 'Georgetown' },
        '78701': { lat: 30.2711, lng: -97.7437, city: 'Austin' },
        '75201': { lat: 32.7872, lng: -96.7985, city: 'Dallas' },
        '75034': { lat: 33.1507, lng: -96.8236, city: 'Frisco' },
        '78681': { lat: 30.5083, lng: -97.6789, city: 'Round Rock' },
        '75024': { lat: 33.0742, lng: -96.8017, city: 'Plano' },
        '76051': { lat: 32.9343, lng: -97.0781, city: 'Grapevine' },
        '78750': { lat: 30.4524, lng: -97.7920, city: 'Austin' },
        '75070': { lat: 33.1651, lng: -96.6670, city: 'McKinney' }
    };

    if (texasZips[zipCode]) {
        return texasZips[zipCode];
    }

    // If not in our list, try to get from database zip_code_grids
    try {
        const { data } = await supabase
            .from('zip_code_grids')
            .select('latitude, longitude, city')
            .eq('zip_code', zipCode)
            .single();

        if (data && data.latitude) {
            return { lat: data.latitude, lng: data.longitude, city: data.city };
        }
    } catch (e) {
        // Ignore
    }

    return null;
}

// Refresh map after discovery
async function refreshMap() {
    await loadLeadsOnMap();
}

// ========================================
// DISCOVERY MAP FUNCTIONS
// ========================================

// Discovery map state
let discoveryMap = null;
let expandedMap = null;
let discoveryPin = null;
let discoveryCircle = null;
let expandedPin = null;
let expandedCircle = null;
let selectedLocation = null;
let isSatelliteView = false;

// Tile layers
const streetTiles = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const satelliteTiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

// Current mode: 'form' or 'map'
let inputMode = 'form';

// Initialize discovery map (mini version in panel)
function initDiscoveryMap() {
    if (discoveryMap) return; // Already initialized

    const mapContainer = document.getElementById('discovery-map');
    if (!mapContainer) return;

    // Center on Texas
    discoveryMap = L.map('discovery-map').setView([31.0, -97.5], 7);

    // Add street tiles by default
    L.tileLayer(streetTiles, {
        attribution: '© OpenStreetMap',
        maxZoom: 18
    }).addTo(discoveryMap);

    // Click handler to place pin
    discoveryMap.on('click', function(e) {
        placeDiscoveryPin(e.latlng, discoveryMap, 'mini');
    });
}

// Initialize expanded map modal
function initExpandedMap() {
    if (expandedMap) return; // Already initialized

    const mapContainer = document.getElementById('expanded-discovery-map');
    if (!mapContainer) return;

    // Center on Texas or current selection
    const center = selectedLocation ? [selectedLocation.lat, selectedLocation.lng] : [31.0, -97.5];
    const zoom = selectedLocation ? 10 : 7;

    expandedMap = L.map('expanded-discovery-map').setView(center, zoom);

    // Add street tiles by default
    expandedMap.tileLayer = L.tileLayer(streetTiles, {
        attribution: '© OpenStreetMap',
        maxZoom: 18
    }).addTo(expandedMap);

    // Click handler to place pin
    expandedMap.on('click', function(e) {
        placeDiscoveryPin(e.latlng, expandedMap, 'expanded');
    });

    // If we have a selected location, show it
    if (selectedLocation) {
        placeDiscoveryPin({ lat: selectedLocation.lat, lng: selectedLocation.lng }, expandedMap, 'expanded');
    }
}

// Place a pin on the discovery map
function placeDiscoveryPin(latlng, targetMap, mapType) {
    const radiusSlider = mapType === 'expanded' ?
        document.getElementById('modal-radius') :
        document.getElementById('radius');
    const radiusMiles = parseInt(radiusSlider.value) || 15;
    const radiusMeters = radiusMiles * 1609.34;

    // Store the selected location
    selectedLocation = {
        lat: latlng.lat,
        lng: latlng.lng
    };

    // Custom pin icon
    const pinIcon = L.divIcon({
        className: 'discovery-pin',
        iconSize: [24, 36],
        iconAnchor: [12, 36],
        html: `<svg width="24" height="36" viewBox="0 0 24 36" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 0C5.372 0 0 5.372 0 12c0 9 12 24 12 24s12-15 12-24c0-6.628-5.372-12-12-12z" fill="#3535de"/>
            <circle cx="12" cy="12" r="5" fill="white"/>
        </svg>`
    });

    if (mapType === 'mini') {
        // Clear existing pin and circle on mini map
        if (discoveryPin) discoveryMap.removeLayer(discoveryPin);
        if (discoveryCircle) discoveryMap.removeLayer(discoveryCircle);

        // Add new pin
        discoveryPin = L.marker([latlng.lat, latlng.lng], { icon: pinIcon, draggable: true })
            .addTo(discoveryMap);

        // Add radius circle
        discoveryCircle = L.circle([latlng.lat, latlng.lng], {
            radius: radiusMeters,
            color: '#3535de',
            fillColor: '#3535de',
            fillOpacity: 0.15,
            weight: 2
        }).addTo(discoveryMap);

        // Allow dragging the pin
        discoveryPin.on('drag', function(e) {
            const pos = e.target.getLatLng();
            selectedLocation = { lat: pos.lat, lng: pos.lng };
            discoveryCircle.setLatLng(pos);
            updatePinInfo();
        });

        // Fit to circle bounds
        discoveryMap.fitBounds(discoveryCircle.getBounds(), { padding: [20, 20] });

    } else {
        // Clear existing pin and circle on expanded map
        if (expandedPin) expandedMap.removeLayer(expandedPin);
        if (expandedCircle) expandedMap.removeLayer(expandedCircle);

        // Add new pin
        expandedPin = L.marker([latlng.lat, latlng.lng], { icon: pinIcon, draggable: true })
            .addTo(expandedMap);

        // Add radius circle
        expandedCircle = L.circle([latlng.lat, latlng.lng], {
            radius: radiusMeters,
            color: '#3535de',
            fillColor: '#3535de',
            fillOpacity: 0.15,
            weight: 2
        }).addTo(expandedMap);

        // Allow dragging the pin
        expandedPin.on('drag', function(e) {
            const pos = e.target.getLatLng();
            selectedLocation = { lat: pos.lat, lng: pos.lng };
            expandedCircle.setLatLng(pos);
            updateModalPinInfo();
        });

        // Fit to circle bounds
        expandedMap.fitBounds(expandedCircle.getBounds(), { padding: [30, 30] });

        // Enable confirm button
        document.getElementById('confirm-map-selection').disabled = false;
    }

    // Update info displays
    updatePinInfo();
    updateModalPinInfo();
}

// Update the radius circle when slider changes
function updateDiscoveryRadius(mapType) {
    const radiusSlider = mapType === 'expanded' ?
        document.getElementById('modal-radius') :
        document.getElementById('radius');
    const radiusDisplay = mapType === 'expanded' ?
        document.getElementById('modal-radius-display') :
        document.getElementById('radius-display');

    const radiusMiles = parseInt(radiusSlider.value) || 15;
    const radiusMeters = radiusMiles * 1609.34;

    // Update display
    radiusDisplay.textContent = radiusMiles;

    // Update circle if exists
    if (mapType === 'mini' && discoveryCircle) {
        discoveryCircle.setRadius(radiusMeters);
        discoveryMap.fitBounds(discoveryCircle.getBounds(), { padding: [20, 20] });
    } else if (mapType === 'expanded' && expandedCircle) {
        expandedCircle.setRadius(radiusMeters);
        expandedMap.fitBounds(expandedCircle.getBounds(), { padding: [30, 30] });
    }

    // Update info
    updatePinInfo();
    updateModalPinInfo();
}

// Update pin info display
function updatePinInfo() {
    const pinInfo = document.getElementById('pin-info');
    const pinLocation = document.getElementById('pin-location');

    if (selectedLocation && inputMode === 'map') {
        pinInfo.classList.remove('hidden');
        pinLocation.textContent = `${selectedLocation.lat.toFixed(4)}, ${selectedLocation.lng.toFixed(4)}`;
    } else {
        pinInfo.classList.add('hidden');
    }
}

// Update modal pin info display
function updateModalPinInfo() {
    const modalPinInfo = document.getElementById('modal-pin-info');
    const confirmBtn = document.getElementById('confirm-map-selection');

    if (selectedLocation) {
        const radius = document.getElementById('modal-radius').value;
        modalPinInfo.textContent = `Selected: ${selectedLocation.lat.toFixed(4)}, ${selectedLocation.lng.toFixed(4)} (${radius} mi radius)`;
        confirmBtn.disabled = false;
    } else {
        modalPinInfo.textContent = 'Click on the map to place a pin';
        confirmBtn.disabled = true;
    }
}

// Toggle satellite view
function toggleSatelliteView(targetMap, mapType) {
    isSatelliteView = !isSatelliteView;

    const tileUrl = isSatelliteView ? satelliteTiles : streetTiles;
    const attribution = isSatelliteView ? '© Esri' : '© OpenStreetMap';

    // Remove existing tiles and add new ones
    targetMap.eachLayer(function(layer) {
        if (layer instanceof L.TileLayer) {
            targetMap.removeLayer(layer);
        }
    });

    L.tileLayer(tileUrl, {
        attribution: attribution,
        maxZoom: 18
    }).addTo(targetMap);

    // Update button text
    const btn = mapType === 'expanded' ?
        document.getElementById('modal-toggle-satellite') :
        document.getElementById('toggle-satellite');

    if (btn) {
        btn.classList.toggle('active', isSatelliteView);
    }
}

// Switch between form and map input modes
function switchInputMode(mode) {
    inputMode = mode;

    const formMode = document.getElementById('form-input-mode');
    const mapMode = document.getElementById('map-input-mode');
    const formBtn = document.getElementById('mode-form');
    const mapBtn = document.getElementById('mode-map');

    if (mode === 'form') {
        formMode.classList.remove('hidden');
        mapMode.classList.add('hidden');
        formBtn.classList.add('active');
        mapBtn.classList.remove('active');
    } else {
        formMode.classList.add('hidden');
        mapMode.classList.remove('hidden');
        formBtn.classList.remove('active');
        mapBtn.classList.add('active');

        // Initialize discovery map if not already done
        setTimeout(() => {
            initDiscoveryMap();
            // Force map to recalculate size
            if (discoveryMap) {
                discoveryMap.invalidateSize();
            }
        }, 100);
    }

    updatePinInfo();
}

// Open expanded map modal
function openMapModal() {
    const modal = document.getElementById('map-modal');
    modal.classList.remove('hidden');

    // Initialize expanded map
    setTimeout(() => {
        initExpandedMap();
        if (expandedMap) {
            expandedMap.invalidateSize();

            // Sync radius slider
            const mainRadius = document.getElementById('radius').value;
            document.getElementById('modal-radius').value = mainRadius;
            document.getElementById('modal-radius-display').textContent = mainRadius;

            // If we have a selected location, show it on expanded map too
            if (selectedLocation) {
                placeDiscoveryPin({ lat: selectedLocation.lat, lng: selectedLocation.lng }, expandedMap, 'expanded');
            }
        }
    }, 100);
}

// Close expanded map modal
function closeMapModal() {
    const modal = document.getElementById('map-modal');
    modal.classList.add('hidden');
}

// Confirm map selection and sync back to main panel
function confirmMapSelection() {
    if (!selectedLocation) return;

    // Sync radius from modal to main
    const modalRadius = document.getElementById('modal-radius').value;
    document.getElementById('radius').value = modalRadius;
    document.getElementById('radius-display').textContent = modalRadius;

    // Switch to map mode if not already
    if (inputMode !== 'map') {
        switchInputMode('map');
    }

    // Update mini map with the selection
    setTimeout(() => {
        if (discoveryMap) {
            placeDiscoveryPin({ lat: selectedLocation.lat, lng: selectedLocation.lng }, discoveryMap, 'mini');
        }
    }, 150);

    // Close modal
    closeMapModal();

    showToast('Location selected! Click "Start Discovery" to begin.', 'success');
}

// Setup discovery map event listeners
function setupDiscoveryMapListeners() {
    // Mode toggle buttons
    const formBtn = document.getElementById('mode-form');
    const mapBtn = document.getElementById('mode-map');

    if (formBtn) {
        formBtn.addEventListener('click', () => switchInputMode('form'));
    }
    if (mapBtn) {
        mapBtn.addEventListener('click', () => switchInputMode('map'));
    }

    // Radius slider for mini map
    const radiusSlider = document.getElementById('radius');
    if (radiusSlider) {
        radiusSlider.addEventListener('input', () => {
            document.getElementById('radius-display').textContent = radiusSlider.value;
            if (inputMode === 'map') {
                updateDiscoveryRadius('mini');
            }
        });
    }

    // Radius slider for expanded map
    const modalRadiusSlider = document.getElementById('modal-radius');
    if (modalRadiusSlider) {
        modalRadiusSlider.addEventListener('input', () => {
            document.getElementById('modal-radius-display').textContent = modalRadiusSlider.value;
            updateDiscoveryRadius('expanded');
        });
    }

    // Satellite toggle for mini map
    const toggleSatBtn = document.getElementById('toggle-satellite');
    if (toggleSatBtn) {
        toggleSatBtn.addEventListener('click', () => {
            if (discoveryMap) toggleSatelliteView(discoveryMap, 'mini');
        });
    }

    // Satellite toggle for expanded map
    const modalToggleSatBtn = document.getElementById('modal-toggle-satellite');
    if (modalToggleSatBtn) {
        modalToggleSatBtn.addEventListener('click', () => {
            if (expandedMap) toggleSatelliteView(expandedMap, 'expanded');
        });
    }

    // Expand map button
    const expandBtn = document.getElementById('expand-discovery-map');
    if (expandBtn) {
        expandBtn.addEventListener('click', openMapModal);
    }

    // Close modal button
    const closeBtn = document.getElementById('close-map-modal');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeMapModal);
    }

    // Confirm selection button
    const confirmBtn = document.getElementById('confirm-map-selection');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', confirmMapSelection);
    }

    // Close modal on outside click
    const modal = document.getElementById('map-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeMapModal();
        });
    }
}

// Override runDiscovery to handle map mode
const originalRunDiscovery = runDiscovery;
runDiscovery = async function() {
    // If in map mode, we use the selected location coordinates
    if (inputMode === 'map' && selectedLocation) {
        const radius = parseInt(document.getElementById('radius').value) || 15;

        // Disable button
        elements.runDiscovery.disabled = true;
        elements.runDiscovery.innerHTML = `
            <svg class="spin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12a9 9 0 11-6.219-8.56"/>
            </svg>
            Running...
        `;

        // Show status
        elements.discoveryStatus.classList.remove('hidden', 'success', 'error');
        elements.statusText.textContent = 'Starting discovery...';
        elements.statusDetails.innerHTML = '<p>Searching from map pin location...</p>';

        try {
            // Call edge function with coordinates
            const response = await fetch(`${SUPABASE_URL}/functions/v1/discover-leads`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    latitude: selectedLocation.lat,
                    longitude: selectedLocation.lng,
                    radius_miles: radius
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Discovery failed');
            }

            // Show success
            elements.discoveryStatus.classList.add('success');
            elements.statusText.textContent = 'Discovery completed!';
            elements.statusDetails.innerHTML = `
                <p><strong>Job ID:</strong> ${result.job_id}</p>
                <p><strong>Location:</strong> ${selectedLocation.lat.toFixed(4)}, ${selectedLocation.lng.toFixed(4)}</p>
                <p><strong>Places Found:</strong> ${result.stats.places_found}</p>
                <p><strong>Leads Created:</strong> ${result.stats.leads_created}</p>
                <p><strong>Filtered Out:</strong> ${result.stats.leads_filtered}</p>
                <p><strong>Duplicates:</strong> ${result.stats.duplicates_skipped}</p>
                <p><strong>Est. Cost:</strong> $${(result.stats.estimated_cost_cents / 100).toFixed(2)}</p>
            `;

            showToast(`Created ${result.stats.leads_created} new leads!`, 'success');

            // Refresh data
            await Promise.all([
                loadStats(),
                loadRecentJobs(),
                loadMetroStats(),
                loadLeadsOnMap()
            ]);

        } catch (err) {
            console.error('Discovery error:', err);
            elements.discoveryStatus.classList.add('error');
            elements.statusText.textContent = 'Discovery failed';
            elements.statusDetails.innerHTML = `<p>${err.message}</p>`;
            showToast('Discovery failed: ' + err.message, 'error');
        } finally {
            // Re-enable button
            elements.runDiscovery.disabled = false;
            elements.runDiscovery.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                Start Discovery
            `;
        }
    } else {
        // Use original form-based discovery
        await originalRunDiscovery();
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    init();
    setupDiscoveryMapListeners();
    setupEnrichmentQueues();
});

// ========================================
// CLAY ENRICHMENT QUEUE FUNCTIONS
// ========================================

// Enrichment state
const enrichmentState = {
    builtwithQueue: [],
    waterfallQueue: [],
    exports: JSON.parse(localStorage.getItem('enrichmentExports') || '[]'),
    notifications: JSON.parse(localStorage.getItem('notificationSettings') || '{}')
};

// Setup enrichment queue event listeners
function setupEnrichmentQueues() {
    // Refresh buttons
    document.getElementById('refresh-builtwith-queue')?.addEventListener('click', loadBuiltWithQueue);
    document.getElementById('refresh-waterfall-queue')?.addEventListener('click', loadWaterfallQueue);

    // Export buttons
    document.getElementById('export-builtwith-csv')?.addEventListener('click', () => exportCSV('builtwith'));
    document.getElementById('export-waterfall-csv')?.addEventListener('click', () => exportCSV('waterfall'));

    // Import buttons - trigger file input
    document.getElementById('import-builtwith-csv')?.addEventListener('click', () => {
        document.getElementById('import-builtwith-file')?.click();
    });
    document.getElementById('import-waterfall-csv')?.addEventListener('click', () => {
        document.getElementById('import-waterfall-file')?.click();
    });

    // File input change handlers
    document.getElementById('import-builtwith-file')?.addEventListener('change', (e) => {
        if (e.target.files?.length) {
            importCSV('builtwith', e.target.files[0]);
            e.target.value = ''; // Reset for next import
        }
    });
    document.getElementById('import-waterfall-file')?.addEventListener('change', (e) => {
        if (e.target.files?.length) {
            importCSV('waterfall', e.target.files[0]);
            e.target.value = ''; // Reset for next import
        }
    });

    // Notification settings
    const enableNotifications = document.getElementById('enable-email-notifications');
    if (enableNotifications) {
        enableNotifications.checked = enrichmentState.notifications.enabled || false;
        document.getElementById('email-settings')?.classList.toggle('hidden', !enableNotifications.checked);

        enableNotifications.addEventListener('change', (e) => {
            document.getElementById('email-settings')?.classList.toggle('hidden', !e.target.checked);
        });
    }

    // Load saved notification settings
    if (enrichmentState.notifications.email) {
        const emailInput = document.getElementById('notification-email');
        if (emailInput) emailInput.value = enrichmentState.notifications.email;
    }
    if (enrichmentState.notifications.builtwithThreshold) {
        const thresholdInput = document.getElementById('builtwith-threshold');
        if (thresholdInput) thresholdInput.value = enrichmentState.notifications.builtwithThreshold;
    }
    if (enrichmentState.notifications.waterfallThreshold) {
        const thresholdInput = document.getElementById('waterfall-threshold');
        if (thresholdInput) thresholdInput.value = enrichmentState.notifications.waterfallThreshold;
    }

    // Save notification settings button
    document.getElementById('save-notification-settings')?.addEventListener('click', saveNotificationSettings);

    // Load initial data
    loadBuiltWithQueue();
    loadWaterfallQueue();
    renderExportsTable();
}

// Load BuiltWith enrichment queue
async function loadBuiltWithQueue() {
    try {
        // Leads that need tech enrichment:
        // - Have a website
        // - tech_analysis_at is NULL (tech enrichment not done)
        const { data: pendingLeads, error: pendingError } = await supabase
            .from('leads')
            .select('id, business_name, website, address_city, address_state, phone, discovered_at')
            .not('website', 'is', null)
            .is('tech_analysis_at', null)
            .order('discovered_at', { ascending: false });

        if (pendingError) throw pendingError;

        // Count completed
        const { count: completedCount, error: completedError } = await supabase
            .from('leads')
            .select('*', { count: 'exact', head: true })
            .not('tech_analysis_at', 'is', null);

        if (completedError) throw completedError;

        enrichmentState.builtwithQueue = pendingLeads || [];

        // Update UI
        document.getElementById('builtwith-queue-count').textContent = enrichmentState.builtwithQueue.length;
        document.getElementById('builtwith-completed-count').textContent = completedCount || 0;

        // Check notification threshold
        checkNotificationThreshold('builtwith', enrichmentState.builtwithQueue.length);

    } catch (err) {
        console.error('Error loading BuiltWith queue:', err);
        showToast('Failed to load BuiltWith queue', 'error');
    }
}

// Load Waterfall (contact) enrichment queue
async function loadWaterfallQueue() {
    try {
        // Leads that need contact enrichment:
        // - tech_analysis_at is NOT NULL (tech enrichment done)
        // - phase_3_completed_at is NOT NULL (pain scoring done)
        // - qualification_status = 'qualified'
        // - owner_email is NULL (contact enrichment not done)
        const { data: pendingLeads, error: pendingError } = await supabase
            .from('leads')
            .select('id, business_name, website, address_city, address_state, phone, pain_point_score, tech_analysis_at')
            .not('tech_analysis_at', 'is', null)
            .not('phase_3_completed_at', 'is', null)
            .eq('qualification_status', 'qualified')
            .is('owner_email', null)
            .order('pain_point_score', { ascending: false });

        if (pendingError) throw pendingError;

        // Count completed (leads with owner_email populated)
        const { count: completedCount, error: completedError } = await supabase
            .from('leads')
            .select('*', { count: 'exact', head: true })
            .not('owner_email', 'is', null);

        if (completedError) throw completedError;

        enrichmentState.waterfallQueue = pendingLeads || [];

        // Update UI
        document.getElementById('waterfall-queue-count').textContent = enrichmentState.waterfallQueue.length;
        document.getElementById('waterfall-completed-count').textContent = completedCount || 0;

        // Check notification threshold
        checkNotificationThreshold('waterfall', enrichmentState.waterfallQueue.length);

    } catch (err) {
        console.error('Error loading Waterfall queue:', err);
        showToast('Failed to load Waterfall queue', 'error');
    }
}

// Export CSV for Clay import
async function exportCSV(type) {
    const statusEl = document.getElementById(`${type}-status`);
    const statusText = document.getElementById(`${type}-status-text`);
    const exportBtn = document.getElementById(`export-${type}-csv`);

    try {
        // Show loading state
        statusEl?.classList.remove('hidden', 'success', 'error');
        if (statusText) statusText.textContent = 'Generating CSV...';
        if (exportBtn) exportBtn.disabled = true;

        let leads = [];
        let filename = '';
        let headers = [];

        if (type === 'builtwith') {
            // Fetch full data for BuiltWith export
            const { data, error } = await supabase
                .from('leads')
                .select('id, business_name, website, phone, address_full, address_city, address_state, address_zip, google_rating, google_review_count')
                .not('website', 'is', null)
                .is('phase_1_completed_at', null)
                .order('discovered_at', { ascending: false });

            if (error) throw error;
            leads = data || [];

            headers = ['lead_id', 'business_name', 'website', 'phone', 'address', 'city', 'state', 'zip', 'google_rating', 'review_count'];
            filename = `builtwith_enrichment_${new Date().toISOString().split('T')[0]}.csv`;

        } else if (type === 'waterfall') {
            // Fetch full data for Waterfall export
            const { data, error } = await supabase
                .from('leads')
                .select('id, business_name, website, phone, address_full, address_city, address_state, address_zip, pain_point_score, tech_stack_ai_score, cms_platform_ai, has_crm')
                .not('tech_analysis_at', 'is', null)
                .not('phase_3_completed_at', 'is', null)
                .eq('qualification_status', 'qualified')
                .is('owner_email', null)
                .order('pain_point_score', { ascending: false });

            if (error) throw error;
            leads = data || [];

            headers = ['lead_id', 'business_name', 'website', 'phone', 'address', 'city', 'state', 'zip', 'pain_score', 'tech_score', 'cms', 'crm'];
            filename = `waterfall_enrichment_${new Date().toISOString().split('T')[0]}.csv`;
        }

        if (leads.length === 0) {
            throw new Error('No leads to export');
        }

        // Generate CSV content
        const csvRows = [headers.join(',')];

        leads.forEach(lead => {
            const row = type === 'builtwith' ? [
                lead.id,
                escapeCSV(lead.business_name),
                escapeCSV(lead.website),
                escapeCSV(lead.phone || ''),
                escapeCSV(lead.address_full || ''),
                escapeCSV(lead.address_city || ''),
                escapeCSV(lead.address_state || ''),
                escapeCSV(lead.address_zip || ''),
                lead.google_rating || '',
                lead.google_review_count || ''
            ] : [
                lead.id,
                escapeCSV(lead.business_name),
                escapeCSV(lead.website),
                escapeCSV(lead.phone || ''),
                escapeCSV(lead.address_full || ''),
                escapeCSV(lead.address_city || ''),
                escapeCSV(lead.address_state || ''),
                escapeCSV(lead.address_zip || ''),
                lead.pain_point_score || '',
                lead.tech_stack_ai_score || '',
                escapeCSV(lead.cms_platform_ai || ''),
                lead.has_crm ? 'Yes' : 'No'
            ];
            csvRows.push(row.join(','));
        });

        const csvContent = csvRows.join('\n');

        // Download the file
        downloadCSV(csvContent, filename);

        // Save export record
        const exportRecord = {
            id: Date.now(),
            date: new Date().toISOString(),
            type: type === 'builtwith' ? 'BuiltWith' : 'Waterfall',
            leads: leads.length,
            filename: filename,
            status: 'ready'
        };

        enrichmentState.exports.unshift(exportRecord);
        enrichmentState.exports = enrichmentState.exports.slice(0, 20); // Keep last 20
        localStorage.setItem('enrichmentExports', JSON.stringify(enrichmentState.exports));
        renderExportsTable();

        // Show success
        statusEl?.classList.add('success');
        if (statusText) statusText.textContent = `Exported ${leads.length} leads to ${filename}`;
        showToast(`CSV exported successfully! ${leads.length} leads ready for Clay import.`, 'success');

        // Send email notification if enabled
        if (enrichmentState.notifications.enabled && enrichmentState.notifications.email) {
            sendExportNotification(type, leads.length, filename);
        }

    } catch (err) {
        console.error('Export error:', err);
        statusEl?.classList.add('error');
        if (statusText) statusText.textContent = err.message || 'Export failed';
        showToast('CSV export failed: ' + err.message, 'error');
    } finally {
        if (exportBtn) exportBtn.disabled = false;
    }
}

// Escape CSV values
function escapeCSV(value) {
    if (!value) return '';
    const str = String(value);
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return '"' + str.replace(/"/g, '""') + '"';
    }
    return str;
}

// Download CSV file
function downloadCSV(content, filename) {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Render exports table
function renderExportsTable() {
    const tbody = document.getElementById('exports-table');
    if (!tbody) return;

    if (enrichmentState.exports.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No exports yet</td></tr>';
        return;
    }

    tbody.innerHTML = enrichmentState.exports.map(exp => {
        const date = new Date(exp.date).toLocaleString();
        const statusClass = exp.status === 'ready' ? 'ready' :
                           exp.status === 'imported' ? 'imported' : 'processing';

        return `
            <tr>
                <td>${date}</td>
                <td>${exp.type}</td>
                <td><strong>${exp.leads}</strong></td>
                <td><span class="status-badge ${statusClass}">${exp.status}</span></td>
                <td>
                    <button class="btn btn-download btn-sm" onclick="markAsImported(${exp.id})" title="Mark as imported to Clay">
                        ${exp.status === 'imported' ? 'Done' : 'Mark Imported'}
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// Mark export as imported
window.markAsImported = function(exportId) {
    const exportIndex = enrichmentState.exports.findIndex(e => e.id === exportId);
    if (exportIndex !== -1) {
        enrichmentState.exports[exportIndex].status = 'imported';
        localStorage.setItem('enrichmentExports', JSON.stringify(enrichmentState.exports));
        renderExportsTable();
        showToast('Export marked as imported', 'success');
    }
};

// Check notification threshold
function checkNotificationThreshold(type, count) {
    if (!enrichmentState.notifications.enabled) return;

    const threshold = type === 'builtwith' ?
        enrichmentState.notifications.builtwithThreshold :
        enrichmentState.notifications.waterfallThreshold;

    if (threshold && count >= threshold) {
        // Check if we've already notified for this threshold
        const lastNotified = localStorage.getItem(`lastNotified_${type}`);
        const now = Date.now();

        // Only notify once per hour
        if (!lastNotified || (now - parseInt(lastNotified)) > 3600000) {
            showToast(`${type === 'builtwith' ? 'BuiltWith' : 'Waterfall'} queue has ${count} leads ready for export!`, 'info');
            localStorage.setItem(`lastNotified_${type}`, now.toString());
        }
    }
}

// Save notification settings
function saveNotificationSettings() {
    enrichmentState.notifications = {
        enabled: document.getElementById('enable-email-notifications')?.checked || false,
        email: document.getElementById('notification-email')?.value || '',
        builtwithThreshold: parseInt(document.getElementById('builtwith-threshold')?.value) || 25,
        waterfallThreshold: parseInt(document.getElementById('waterfall-threshold')?.value) || 25
    };

    localStorage.setItem('notificationSettings', JSON.stringify(enrichmentState.notifications));
    showToast('Notification settings saved!', 'success');
}

// Send export notification email via Supabase Edge Function
async function sendExportNotification(type, leadCount, filename) {
    const email = enrichmentState.notifications.email;
    if (!email) {
        console.log('No notification email configured');
        return;
    }

    const typeName = type === 'builtwith' ? 'BuiltWith' : 'Waterfall';

    try {
        const response = await fetch(`${SUPABASE_URL}/functions/v1/send-notification`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                to: email,
                subject: `Rise Local: ${typeName} Export Ready - ${leadCount} Leads`,
                body: `Import this file to Clay to continue the enrichment process.`,
                type: type,
                leadCount: leadCount,
                filename: filename
            })
        });

        const result = await response.json();

        if (response.ok) {
            console.log('Email notification sent:', result);
            showToast(`Notification sent to ${email}`, 'info');
        } else {
            console.error('Failed to send notification:', result);
        }
    } catch (err) {
        console.error('Error sending notification:', err);
    }
}

// Auto-refresh enrichment queues every 60 seconds
setInterval(() => {
    loadBuiltWithQueue();
    loadWaterfallQueue();
}, 60000);

// ========================================
// CSV IMPORT FUNCTIONS
// ========================================

// Import enriched CSV from Clay back into Supabase
async function importCSV(type, file) {
    const statusEl = document.getElementById(`${type}-status`);
    const statusText = document.getElementById(`${type}-status-text`);
    const importBtn = document.getElementById(`import-${type}-csv`);

    try {
        // Show loading state
        statusEl?.classList.remove('hidden', 'success', 'error');
        if (statusText) statusText.textContent = 'Parsing CSV...';
        if (importBtn) importBtn.disabled = true;

        // Read and parse CSV
        const csvText = await file.text();
        const rows = parseCSV(csvText);

        if (rows.length < 2) {
            throw new Error('CSV file is empty or has no data rows');
        }

        const headers = rows[0].map(h => h.toLowerCase().trim());
        const dataRows = rows.slice(1);

        if (statusText) statusText.textContent = `Processing ${dataRows.length} leads...`;

        let successCount = 0;
        let errorCount = 0;

        if (type === 'builtwith') {
            // BuiltWith import - update tech enrichment fields
            // Expected columns from Clay: lead_id, has_gtm, has_ga4, cms_platform, crm_platform, has_booking_system, tech_stack_score, etc.

            const leadIdIndex = headers.findIndex(h => h === 'lead_id' || h === 'id');
            if (leadIdIndex === -1) {
                throw new Error('CSV must have a "lead_id" or "id" column to match leads');
            }

            for (const row of dataRows) {
                const leadId = row[leadIdIndex]?.trim();
                if (!leadId) continue;

                // Build update object from available columns
                const updateData = {
                    phase_1_completed_at: new Date().toISOString()
                };

                // Map CSV columns to database fields
                const columnMappings = {
                    'has_gtm': 'has_gtm',
                    'has_ga4': 'has_ga4',
                    'cms_platform': 'cms_platform',
                    'cms': 'cms_platform',
                    'crm_platform': 'crm_platform',
                    'crm': 'crm_platform',
                    'has_booking_system': 'has_booking_system',
                    'booking_system': 'has_booking_system',
                    'tech_stack_score': 'tech_stack_score',
                    'tech_score': 'tech_stack_score',
                    'has_chat_widget': 'has_chat_widget',
                    'chat_widget': 'has_chat_widget'
                };

                for (const [csvCol, dbCol] of Object.entries(columnMappings)) {
                    const colIndex = headers.indexOf(csvCol);
                    if (colIndex !== -1 && row[colIndex] !== undefined && row[colIndex] !== '') {
                        let value = row[colIndex].trim();
                        // Convert boolean strings
                        if (value.toLowerCase() === 'true' || value === '1') value = true;
                        else if (value.toLowerCase() === 'false' || value === '0') value = false;
                        // Convert numbers
                        else if (!isNaN(value) && value !== '') value = parseFloat(value);

                        updateData[dbCol] = value;
                    }
                }

                // Update the lead in Supabase
                const { error } = await supabase
                    .from('leads')
                    .update(updateData)
                    .eq('id', leadId);

                if (error) {
                    console.error(`Error updating lead ${leadId}:`, error);
                    errorCount++;
                } else {
                    successCount++;
                }
            }

        } else if (type === 'waterfall') {
            // Contact Waterfall import - update contact fields
            // Expected columns from Clay: lead_id, owner_email, owner_first_name, owner_last_name, owner_linkedin_url, etc.

            const leadIdIndex = headers.findIndex(h => h === 'lead_id' || h === 'id');
            if (leadIdIndex === -1) {
                throw new Error('CSV must have a "lead_id" or "id" column to match leads');
            }

            for (const row of dataRows) {
                const leadId = row[leadIdIndex]?.trim();
                if (!leadId) continue;

                // Build update object from available columns
                const updateData = {
                    phase_4_completed_at: new Date().toISOString()
                };

                // Map CSV columns to database fields
                const columnMappings = {
                    'owner_email': 'owner_email',
                    'email': 'owner_email',
                    'owner_first_name': 'owner_first_name',
                    'first_name': 'owner_first_name',
                    'firstname': 'owner_first_name',
                    'owner_last_name': 'owner_last_name',
                    'last_name': 'owner_last_name',
                    'lastname': 'owner_last_name',
                    'owner_linkedin_url': 'owner_linkedin_url',
                    'linkedin_url': 'owner_linkedin_url',
                    'linkedin': 'owner_linkedin_url',
                    'owner_phone': 'owner_phone',
                    'phone_direct': 'owner_phone',
                    'verified_email': 'verified_email',
                    'email_verified': 'verified_email',
                    'owner_source': 'owner_source',
                    'source': 'owner_source'
                };

                for (const [csvCol, dbCol] of Object.entries(columnMappings)) {
                    const colIndex = headers.indexOf(csvCol);
                    if (colIndex !== -1 && row[colIndex] !== undefined && row[colIndex] !== '') {
                        let value = row[colIndex].trim();
                        // Convert boolean strings
                        if (value.toLowerCase() === 'true' || value === '1') value = true;
                        else if (value.toLowerCase() === 'false' || value === '0') value = false;

                        updateData[dbCol] = value;
                    }
                }

                // Update the lead in Supabase
                const { error } = await supabase
                    .from('leads')
                    .update(updateData)
                    .eq('id', leadId);

                if (error) {
                    console.error(`Error updating lead ${leadId}:`, error);
                    errorCount++;
                } else {
                    successCount++;
                }
            }
        }

        // Show results
        statusEl?.classList.add('success');
        if (statusText) statusText.textContent = `Imported ${successCount} leads successfully${errorCount > 0 ? `, ${errorCount} errors` : ''}`;
        showToast(`Imported ${successCount} leads from Clay!`, 'success');

        // Refresh the queues
        await loadBuiltWithQueue();
        await loadWaterfallQueue();
        await loadStats();

    } catch (err) {
        console.error('Import error:', err);
        statusEl?.classList.add('error');
        if (statusText) statusText.textContent = err.message || 'Import failed';
        showToast('CSV import failed: ' + err.message, 'error');
    } finally {
        if (importBtn) importBtn.disabled = false;
    }
}

// Parse CSV text into array of arrays
function parseCSV(text) {
    const rows = [];
    let currentRow = [];
    let currentCell = '';
    let insideQuotes = false;

    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        const nextChar = text[i + 1];

        if (insideQuotes) {
            if (char === '"' && nextChar === '"') {
                // Escaped quote
                currentCell += '"';
                i++;
            } else if (char === '"') {
                // End of quoted field
                insideQuotes = false;
            } else {
                currentCell += char;
            }
        } else {
            if (char === '"') {
                // Start of quoted field
                insideQuotes = true;
            } else if (char === ',') {
                // End of cell
                currentRow.push(currentCell);
                currentCell = '';
            } else if (char === '\n' || (char === '\r' && nextChar === '\n')) {
                // End of row
                currentRow.push(currentCell);
                rows.push(currentRow);
                currentRow = [];
                currentCell = '';
                if (char === '\r') i++; // Skip \n in \r\n
            } else if (char !== '\r') {
                currentCell += char;
            }
        }
    }

    // Don't forget the last cell and row
    if (currentCell || currentRow.length > 0) {
        currentRow.push(currentCell);
        rows.push(currentRow);
    }

    return rows;
}

// ─── State ────────────────────────────────────────────────────────────────────
let currentView = 'landing';
let currentCapability = null;
let currentRegion = null;
let currentTrustFilter = null;
let currentOffset = 0;
let currentTotal = 0;
const PAGE_SIZE = 50;

let navHistory = [];
let cacheReady = false;

const CAP_ICONS = {
    'Emergency': '🚨', 'Maternity': '🤱', 'Cardiology': '❤️',
    'Orthopedics': '🦴', 'Pediatrics': '👶', 'ICU': '🏥',
    'Ophthalmology': '👁️', 'Dental': '🦷', 'Nephrology': '🫘',
    'Neurology': '🧠', 'Oncology': '🎗️', 'Gastroenterology': '🫃',
    'Trauma': '🚑', 'NICU': '👣', 'Dermatology': '🧴',
};

const CAP_COLORS = {
    'ICU': '#3b82f6', 'Maternity': '#ec4899', 'Emergency': '#ef4444',
    'Oncology': '#8b5cf6', 'Trauma': '#f97316', 'NICU': '#06b6d4',
    'Cardiology': '#dc2626', 'Orthopedics': '#84cc16', 'Pediatrics': '#f59e0b',
    'Nephrology': '#14b8a6', 'Neurology': '#a78bfa', 'Ophthalmology': '#0ea5e9',
    'Dental': '#64748b', 'Dermatology': '#d946ef', 'Gastroenterology': '#22c55e',
};

const TRUST_LABELS = {
    'strong_evidence': 'Strong',
    'partial_evidence': 'Partial',
    'weak_evidence': 'Weak',
    'no_claim': 'No Claim',
};

const HERO_GRADIENTS = [
    'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
    'linear-gradient(135deg, #2d1b69 0%, #11998e 100%)',
    'linear-gradient(135deg, #434343 0%, #000000 100%)',
    'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
    'linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)',
];

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadNetflixLanding();
    setupSearch();
    pollCacheStatus();
});

function pollCacheStatus() {
    const check = () => {
        fetch('/api/cache-status').then(r => r.json()).then(data => {
            if (data.ready) {
                cacheReady = true;
                document.getElementById('cacheStatus').style.display = 'none';
            } else {
                setTimeout(check, 2000);
            }
        }).catch(() => setTimeout(check, 3000));
    };
    check();
}

// ─── Netflix Landing ──────────────────────────────────────────────────────────
async function loadNetflixLanding() {
    const [heroRegions, topFacilities, capabilities, regions, needsReview, strongEvidence] = await Promise.all([
        fetch('/api/hero-regions').then(r => r.json()).catch(() => []),
        fetch('/api/top-facilities?limit=25').then(r => r.json()).catch(() => []),
        fetch('/api/capabilities').then(r => r.json()).catch(() => []),
        fetch('/api/regions').then(r => r.json()).catch(() => []),
        fetch('/api/needs-review?limit=25').then(r => r.json()).catch(() => []),
        fetch('/api/strong-evidence?limit=25').then(r => r.json()).catch(() => []),
    ]);

    window._cachedCapabilities = capabilities;
    window._cachedRegions = regions;

    renderHero(heroRegions);
    renderRegions(regions.slice(0, 25));
    renderCapabilities(capabilities);
    renderTopFacilities(topFacilities);
    renderStrongEvidence(strongEvidence);
    renderNeedsReview(needsReview);
}

function renderHero(regions) {
    const section = document.getElementById('heroSection');
    if (!regions.length) { section.style.display = 'none'; return; }

    const postersHtml = regions.map((r, i) => `
        <div class="hero-poster" style="background: ${HERO_GRADIENTS[i % HERO_GRADIENTS.length]}; background-size: cover; background-position: center;"
             id="heroPoster${i}"
             onclick="navigateTo('facilities', {region: '${escapeAttr(r.region)}'})">
            <div class="hero-poster-content">
                <div class="hero-poster-badge">Top Region</div>
                <div class="hero-poster-title">${escapeHtml(r.region)}</div>
                <div class="hero-poster-subtitle">${r.facility_count.toLocaleString()} facilities</div>
            </div>
        </div>
    `).join('');

    // Load state images async
    regions.forEach((r, i) => {
        const img = new Image();
        img.onload = () => {
            const el = document.getElementById(`heroPoster${i}`);
            if (el) el.style.background = `url('/api/state-image/${encodeURIComponent(r.region)}') center/cover`;
        };
        img.src = `/api/state-image/${encodeURIComponent(r.region)}`;
    });

    const dotsHtml = regions.map((_, i) => `<div class="hero-dot ${i === 0 ? 'active' : ''}" onclick="scrollHero(${i})"></div>`).join('');

    section.innerHTML = `
        <div class="hero-scroll" id="heroScroll">${postersHtml}</div>
        <div class="hero-dots">${dotsHtml}</div>
    `;

    const scroll = document.getElementById('heroScroll');
    scroll.addEventListener('scroll', () => {
        const idx = Math.round(scroll.scrollLeft / scroll.clientWidth);
        document.querySelectorAll('.hero-dot').forEach((d, i) => d.classList.toggle('active', i === idx));
    });
}

function scrollHero(idx) {
    const scroll = document.getElementById('heroScroll');
    scroll.scrollTo({ left: idx * scroll.clientWidth, behavior: 'smooth' });
}

function renderTopFacilities(facilities) {
    const container = document.getElementById('rowTopFacilities');
    if (!facilities.length) { container.innerHTML = '<div class="loading">No data</div>'; return; }
    container.innerHTML = facilities.map(f => {
        const trustClass = f.strong_count > 0 ? 'strong' : 'default';
        return `
            <div class="netflix-card" onclick="openFacilityPopup('${f.facility_id}')">
                <div class="netflix-card-top ${trustClass}">
                    <div class="netflix-card-icon">🏥</div>
                    ${f.top_capability ? `<div class="netflix-card-badge strong">${f.top_capability}</div>` : ''}
                </div>
                <div class="netflix-card-body">
                    <div class="netflix-card-title">${escapeHtml(f.name || f.facility_id)}</div>
                    <div class="netflix-card-sub">${escapeHtml((f.address_city || '') + (f.region ? ', ' + f.region : ''))}</div>
                    <div class="netflix-card-meta"><span>${f.total_citations} citations</span><span>${f.strong_count} strong</span></div>
                </div>
            </div>`;
    }).join('');
}

function renderCapabilities(caps) {
    const container = document.getElementById('rowCapabilities');
    if (!caps.length) { container.innerHTML = '<div class="loading">No data</div>'; return; }
    container.innerHTML = caps.map(c => `
        <div class="netflix-card" onclick="navigateTo('facilities', {capability: '${c.capability}'})">
            <div class="netflix-card-top capability"><div class="netflix-card-icon">${CAP_ICONS[c.capability] || '🏥'}</div></div>
            <div class="netflix-card-body">
                <div class="netflix-card-title">${c.capability}</div>
                <div class="netflix-card-sub">${c.facility_count.toLocaleString()} facilities</div>
            </div>
        </div>
    `).join('');
}

function renderRegions(regions) {
    const container = document.getElementById('rowRegions');
    if (!regions.length) { container.innerHTML = '<div class="loading">No data</div>'; return; }
    container.innerHTML = regions.map(r => `
        <div class="netflix-card" onclick="navigateTo('facilities', {region: '${escapeAttr(r.region)}'})">
            <div class="netflix-card-top region" id="regionCard_${escapeAttr(r.region).replace(/[^a-zA-Z]/g, '')}">
                <div class="netflix-card-icon">📍</div>
            </div>
            <div class="netflix-card-body">
                <div class="netflix-card-title">${escapeHtml(r.region)}</div>
                <div class="netflix-card-sub">${r.facility_count.toLocaleString()} facilities</div>
            </div>
        </div>
    `).join('');
    // Load region images
    regions.forEach(r => {
        const img = new Image();
        const elId = `regionCard_${escapeAttr(r.region).replace(/[^a-zA-Z]/g, '')}`;
        img.onload = () => {
            const el = document.getElementById(elId);
            if (el) { el.style.background = `url('/api/state-image/${encodeURIComponent(r.region)}') center/cover`; el.querySelector('.netflix-card-icon').style.display = 'none'; }
        };
        img.src = `/api/state-image/${encodeURIComponent(r.region)}`;
    });
}

function renderNeedsReview(items) {
    const container = document.getElementById('rowNeedsReview');
    if (!items.length) { container.innerHTML = '<div class="loading">No data</div>'; return; }
    container.innerHTML = items.map(f => `
        <div class="netflix-card" onclick="openFacilityPopup('${f.facility_id}', '${f.capability}')">
            <div class="netflix-card-top review">
                <div class="netflix-card-icon">${CAP_ICONS[f.capability] || '❓'}</div>
                <div class="netflix-card-badge weak">${f.capability}</div>
            </div>
            <div class="netflix-card-body">
                <div class="netflix-card-title">${escapeHtml(f.name || f.facility_id)}</div>
                <div class="netflix-card-sub">${escapeHtml((f.address_city || '') + (f.region ? ', ' + f.region : ''))}</div>
                <div class="netflix-card-meta"><span>${f.match_count} matches</span><span>Weak</span></div>
            </div>
        </div>
    `).join('');
}

function renderStrongEvidence(items) {
    const container = document.getElementById('rowStrongEvidence');
    if (!items.length) { container.innerHTML = '<div class="loading">No data</div>'; return; }
    container.innerHTML = items.map(f => `
        <div class="netflix-card" onclick="openFacilityPopup('${f.facility_id}', '${f.capability}')">
            <div class="netflix-card-top strong">
                <div class="netflix-card-icon">${CAP_ICONS[f.capability] || '✓'}</div>
                <div class="netflix-card-badge strong">${f.capability}</div>
            </div>
            <div class="netflix-card-body">
                <div class="netflix-card-title">${escapeHtml(f.name || f.facility_id)}</div>
                <div class="netflix-card-sub">${escapeHtml((f.address_city || '') + (f.region ? ', ' + f.region : ''))}</div>
                <div class="netflix-card-meta"><span>${f.match_count} matches</span><span>Strong</span></div>
            </div>
        </div>
    `).join('');
}

// ─── Navigation ───────────────────────────────────────────────────────────────
function navigateTo(view, params = {}) {
    navHistory.push({ view: currentView, capability: currentCapability, region: currentRegion });
    if (view === 'facilities') {
        currentCapability = params.capability || null;
        currentRegion = params.region || null;
        currentTrustFilter = null;
        currentOffset = 0;
        showFacilityView();
    }
}

function showLanding() {
    currentView = 'landing';
    currentCapability = null;
    currentRegion = null;
    navHistory = [];
    document.getElementById('landingView').style.display = 'block';
    document.getElementById('facilityView').classList.remove('active');
}

// ─── Facility List View ───────────────────────────────────────────────────────
async function showFacilityView() {
    currentView = 'facilities';
    document.getElementById('landingView').style.display = 'none';
    document.getElementById('facilityView').classList.add('active');

    let title = '';
    if (currentCapability && currentRegion) title = `${currentCapability} — ${currentRegion}`;
    else if (currentCapability) title = `${currentCapability} — Facilities`;
    else if (currentRegion) title = `${currentRegion} — Facilities`;
    document.getElementById('viewTitle').textContent = title;
    document.getElementById('facilityList').innerHTML = '<div class="loading">Loading facilities...</div>';
    document.getElementById('filterPills').innerHTML = '';

    setupCrossFilter();
    await loadFacilities(true);
}

// ─── Cross-filter ─────────────────────────────────────────────────────────────
let crossFilterTags = [];
let crossFilterType = null;
let baseCapability = null;
let baseRegion = null;

function setupCrossFilter() {
    const crossFilter = document.getElementById('crossFilter');
    const input = document.getElementById('crossFilterInput');
    const dropdown = document.getElementById('crossFilterDropdown');
    crossFilterTags = [];
    baseCapability = currentCapability;
    baseRegion = currentRegion;

    if (currentRegion && !currentCapability) {
        crossFilter.style.display = 'block';
        crossFilterType = 'capability';
        input.placeholder = 'Filter by capability (click for suggestions)...';
        input.value = '';
        input.oninput = () => showCrossFilterOptions(input.value);
        input.onfocus = () => showCrossFilterOptions(input.value || '');
        input.onblur = () => setTimeout(() => dropdown.classList.remove('active'), 200);
    } else if (currentCapability && !currentRegion) {
        crossFilter.style.display = 'block';
        crossFilterType = 'region';
        input.placeholder = 'Filter by region/state (click for suggestions)...';
        input.value = '';
        input.oninput = () => showCrossFilterOptions(input.value);
        input.onfocus = () => showCrossFilterOptions(input.value || '');
        input.onblur = () => setTimeout(() => dropdown.classList.remove('active'), 200);
    } else {
        crossFilter.style.display = 'none';
    }
    renderCrossFilterTags();
}

function showCrossFilterOptions(q) {
    const dropdown = document.getElementById('crossFilterDropdown');
    if (!cacheReady) { dropdown.classList.remove('active'); return; }
    const qLower = (q || '').toLowerCase();
    let options = [];
    if (crossFilterType === 'region') {
        options = (window._cachedRegions || []).filter(r => (!qLower || r.region.toLowerCase().includes(qLower)) && !crossFilterTags.includes(r.region)).slice(0, 7);
        dropdown.innerHTML = options.map(r => `<div class="cross-filter-item" onmousedown="addCrossFilterTag('${escapeAttr(r.region)}')">${escapeHtml(r.region)} (${r.facility_count})</div>`).join('');
    } else {
        options = (window._cachedCapabilities || []).filter(c => (!qLower || c.capability.toLowerCase().includes(qLower)) && !crossFilterTags.includes(c.capability)).slice(0, 7);
        dropdown.innerHTML = options.map(c => `<div class="cross-filter-item" onmousedown="addCrossFilterTag('${escapeAttr(c.capability)}')">${c.capability} (${c.facility_count})</div>`).join('');
    }
    if (!options.length) dropdown.innerHTML = '<div class="cross-filter-item" style="color:#666;">No more options</div>';
    dropdown.classList.add('active');
}

function addCrossFilterTag(value) {
    document.getElementById('crossFilterDropdown').classList.remove('active');
    document.getElementById('crossFilterInput').value = '';
    if (!crossFilterTags.includes(value)) crossFilterTags.push(value);
    renderCrossFilterTags();
    applyCrossFilterTags();
}

function removeCrossFilterTag(index) {
    crossFilterTags.splice(index, 1);
    renderCrossFilterTags();
    applyCrossFilterTags();
}

function renderCrossFilterTags() {
    const container = document.getElementById('crossFilter');
    let tagsEl = container.querySelector('.cross-filter-tags');
    if (!tagsEl) {
        tagsEl = document.createElement('div');
        tagsEl.className = 'cross-filter-tags';
        tagsEl.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;';
        container.appendChild(tagsEl);
    }
    tagsEl.innerHTML = crossFilterTags.map((tag, i) => `<span class="cross-filter-active" onclick="removeCrossFilterTag(${i})">${escapeHtml(tag)} &times;</span>`).join('');
}

function applyCrossFilterTags() {
    if (crossFilterType === 'capability') {
        currentCapability = crossFilterTags.length ? crossFilterTags.join(',') : null;
        currentRegion = baseRegion;
    } else if (crossFilterType === 'region') {
        currentRegion = crossFilterTags.length ? crossFilterTags.join(',') : null;
        currentCapability = baseCapability;
    }
    let title = '';
    if (crossFilterType === 'capability') {
        title = crossFilterTags.length ? `${baseRegion} — ${crossFilterTags.join(' + ')}` : `${baseRegion} — Facilities`;
    } else {
        title = crossFilterTags.length ? `${baseCapability} — ${crossFilterTags.join(' + ')}` : `${baseCapability} — Facilities`;
    }
    document.getElementById('viewTitle').textContent = title;
    document.getElementById('facilityList').innerHTML = '<div class="loading">Filtering...</div>';
    currentOffset = 0;
    loadFacilities(true);
}

// ─── Load Facilities ──────────────────────────────────────────────────────────
async function loadFacilities(resetList) {
    if (resetList) currentOffset = 0;
    const params = new URLSearchParams();
    if (currentCapability) params.set('capability', currentCapability);
    if (currentRegion) params.set('region', currentRegion);
    if (currentTrustFilter) params.set('trust_level', currentTrustFilter);
    params.set('limit', PAGE_SIZE);
    params.set('offset', currentOffset);

    const data = await fetch(`/api/facilities?${params}`).then(r => r.json());
    currentTotal = data.total;
    buildFilterPills();

    const listEl = document.getElementById('facilityList');
    const html = data.facilities.map(f => renderFacilityCard(f)).join('');
    if (resetList) {
        listEl.innerHTML = html || '<div class="loading">No facilities found.</div>';
    } else {
        listEl.insertAdjacentHTML('beforeend', html);
    }

    const shown = currentOffset + data.facilities.length;
    const loadMoreEl = document.getElementById('loadMoreContainer');
    if (shown < currentTotal) {
        loadMoreEl.style.display = 'block';
        document.getElementById('loadMoreBtn').onclick = () => {
            currentOffset += PAGE_SIZE;
            document.getElementById('loadMoreBtn').textContent = 'Loading...';
            loadFacilities(false).then(() => { document.getElementById('loadMoreBtn').textContent = 'Load More'; });
        };
    } else {
        loadMoreEl.style.display = 'none';
    }
}

function buildFilterPills() {
    const pills = document.getElementById('filterPills');
    const levels = [
        { key: null, label: 'All' }, { key: 'strong_evidence', label: 'Strong' },
        { key: 'partial_evidence', label: 'Partial' }, { key: 'weak_evidence', label: 'Weak' },
        { key: 'no_claim', label: 'No Claim' },
    ];
    pills.innerHTML = levels.map(l => `<div class="pill ${currentTrustFilter === l.key ? 'active' : ''}" onclick="filterByTrust(${l.key ? "'" + l.key + "'" : 'null'})">${l.label}</div>`).join('');
}

function filterByTrust(level) {
    currentTrustFilter = level;
    currentOffset = 0;
    document.getElementById('facilityList').innerHTML = '<div class="loading">Filtering...</div>';
    loadFacilities(true);
}

function renderFacilityCard(f) {
    const fieldsMatched = safeParseJSON(f.fields_matched, []);
    const citations = safeParseJSON(f.evidence_citations, []);
    const trustLabel = TRUST_LABELS[f.trust_level] || f.trust_level;
    const capColor = CAP_COLORS[f.capability] || '#888';

    return `
        <div class="facility-card" onclick="openFacilityPopup('${f.facility_id}', '${f.capability || ''}')">
            <div class="facility-card-header">
                <div>
                    <div class="facility-name">${escapeHtml(f.name || f.facility_id)}</div>
                    <div class="facility-location">${escapeHtml((f.address_city || '') + (f.region ? ', ' + f.region : ''))}</div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                    ${f.capability ? `<span class="cap-badge" style="background:${capColor}22;color:${capColor};border:1px solid ${capColor}44;">${CAP_ICONS[f.capability] || ''} ${f.capability}</span>` : ''}
                    <div class="trust-badge ${f.trust_level}"><div class="trust-dot ${f.trust_level}"></div>${trustLabel}</div>
                </div>
            </div>
            <div class="facility-meta">
                <span>${fieldsMatched.length} field${fieldsMatched.length !== 1 ? 's' : ''}</span>
                <span>${citations.length} citation${citations.length !== 1 ? 's' : ''}</span>
            </div>
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════════
// UNIFIED FACILITY POPUP
// ═══════════════════════════════════════════════════════════════════════════════
let popupFacilityId = null;
let popupFacilityData = null;
let popupScores = [];
let popupSelectedCap = null;
let popupRescoreResult = null;

async function openFacilityPopup(facilityId, preselectedCap) {
    popupFacilityId = facilityId;
    popupRescoreResult = null;

    const popup = document.getElementById('facilityPopup');
    const body = document.getElementById('popupBody');
    body.innerHTML = '<div class="loading">Loading facility...</div>';
    document.getElementById('popupTabs').innerHTML = '';
    document.getElementById('popupTitle').textContent = 'Loading...';
    document.getElementById('popupSubtitle').textContent = '';
    popup.classList.add('active');

    try {
        const resp = await fetch(`/api/facility/${encodeURIComponent(facilityId)}`);
        if (!resp.ok) {
            body.innerHTML = `<div class="loading">Error: ${resp.status} ${resp.statusText}</div>`;
            return;
        }
        const data = await resp.json();
        if (data.error || !data.facility) {
            body.innerHTML = `<div class="loading">${data.error || 'Facility not found'}</div>`;
            return;
        }

        popupFacilityData = data.facility;
        popupScores = data.scores || [];

        document.getElementById('popupTitle').textContent = data.facility.name || facilityId;
        document.getElementById('popupSubtitle').textContent = `${data.facility.address_city || ''}${data.facility.region ? ', ' + data.facility.region : ''}`;

        if (preselectedCap && popupScores.find(s => s.capability === preselectedCap)) {
            popupSelectedCap = preselectedCap;
        } else if (popupScores.length > 0) {
            const best = popupScores.reduce((a, b) => (b.match_count > a.match_count ? b : a), popupScores[0]);
            popupSelectedCap = best.capability;
        } else {
            popupSelectedCap = null;
        }

        renderPopupTabs();
        renderPopupContent();
    } catch (err) {
        body.innerHTML = `<div class="loading">Error: ${err.message}</div>`;
    }
}

function renderPopupTabs() {
    const tabsEl = document.getElementById('popupTabs');
    tabsEl.innerHTML = popupScores.map(s => {
        const color = CAP_COLORS[s.capability] || '#888';
        const dotColor = s.trust_level === 'strong_evidence' ? '#4ade80' : s.trust_level === 'partial_evidence' ? '#fbbf24' : s.trust_level === 'weak_evidence' ? '#fb923c' : '#555';
        const isActive = s.capability === popupSelectedCap;
        return `<div class="popup-tab ${isActive ? 'active' : ''}" onclick="switchPopupTab('${s.capability}')">
            <span class="tab-dot" style="background:${dotColor};"></span>${CAP_ICONS[s.capability] || ''} ${s.capability}
        </div>`;
    }).join('');
}

function switchPopupTab(cap) {
    popupSelectedCap = cap;
    popupRescoreResult = null;
    renderPopupTabs();
    renderPopupContent();
}

function renderPopupContent() {
    const body = document.getElementById('popupBody');
    const score = popupScores.find(s => s.capability === popupSelectedCap);

    if (!score) {
        body.innerHTML = '<div class="loading">No score data for this capability.</div>';
        return;
    }

    const citations = safeParseJSON(score.evidence_citations, []);
    const fieldsMatched = safeParseJSON(score.fields_matched, []);
    const trustLabel = TRUST_LABELS[score.trust_level] || score.trust_level;
    const capColor = CAP_COLORS[score.capability] || '#888';

    let citationsHtml = '';
    if (citations.length) {
        const grouped = {};
        citations.forEach(c => { const f = c.field || 'unknown'; if (!grouped[f]) grouped[f] = []; grouped[f].push(c.text); });
        for (const [field, texts] of Object.entries(grouped)) {
            citationsHtml += `<div class="evidence-section-title">Evidence from: ${field}</div>`;
            texts.forEach(t => {
                citationsHtml += `<div class="citation"><span class="citation-field">${field}</span><span class="citation-text">${escapeHtml(t)}</span></div>`;
            });
        }
    } else {
        citationsHtml = '<p style="font-size:13px;color:#666;padding:8px 0;">No evidence found for this capability.</p>';
    }

    body.innerHTML = `
        <div class="popup-evidence-header">
            <div class="trust-info">
                <div class="trust-badge ${score.trust_level}"><div class="trust-dot ${score.trust_level}"></div>${trustLabel}</div>
                <span class="match-count">${score.match_count} matches across ${fieldsMatched.length} field${fieldsMatched.length !== 1 ? 's' : ''}</span>
            </div>
        </div>
        <div style="margin-bottom:8px;font-size:13px;font-weight:600;color:${capColor};">${CAP_ICONS[score.capability] || ''} ${score.capability}</div>
        ${citationsHtml}
        <button class="edit-toggle-btn" onclick="toggleEditSection()">Edit & Override</button>
        <div class="edit-section" id="editSection">
            ${renderEditFields()}
            <div class="popup-actions">
                <button class="btn-rescore" id="btnRescore" onclick="doPopupRescore()">Re-evaluate</button>
            </div>
            <div class="diff-container" id="popupDiffContainer"></div>
        </div>
    `;
}

function renderEditFields() {
    const score = popupScores.find(s => s.capability === popupSelectedCap);
    const citations = score ? safeParseJSON(score.evidence_citations, []) : [];
    const citationsByField = {};
    citations.forEach(c => {
        const f = c.field || 'unknown';
        if (!citationsByField[f]) citationsByField[f] = [];
        citationsByField[f].push(c.text);
    });

    const fields = ['capability', 'procedure', 'equipment', 'specialties', 'description'];
    let html = '';
    for (const field of fields) {
        const items = [...new Set(citationsByField[field] || [])];
        if (field === 'description') {
            const descText = items.length > 0 ? items.join('\n') : '';
            html += `<div class="edit-field"><div class="edit-field-label">${field}</div><textarea class="edit-field-textarea" id="edit_${field}">${escapeHtml(descText)}</textarea></div>`;
        } else {
            const pillsHtml = items.map((item, i) => `<span class="field-pill" data-value="${escapeAttr(item)}">${escapeHtml(truncate(item, 50))}<span class="field-pill-remove" onclick="removeEditPill(this)">&times;</span></span>`).join('');
            html += `<div class="edit-field"><div class="edit-field-label">${field}</div><div class="edit-field-pills" id="editpills_${field}">${pillsHtml}</div><input type="text" class="edit-field-input" id="editinput_${field}" placeholder="Add ${field} item, press Enter" onkeydown="if(event.key==='Enter'){event.preventDefault();addEditPill('${field}');}"></div>`;
        }
    }
    return html;
}

function toggleEditSection() {
    const section = document.getElementById('editSection');
    section.classList.toggle('active');
}

function removeEditPill(el) { el.parentElement.remove(); }

function addEditPill(field) {
    const input = document.getElementById(`editinput_${field}`);
    const value = input.value.trim();
    if (!value) return;
    const container = document.getElementById(`editpills_${field}`);
    const pill = document.createElement('span');
    pill.className = 'field-pill';
    pill.setAttribute('data-value', value);
    pill.innerHTML = `${escapeHtml(truncate(value, 50))}<span class="field-pill-remove" onclick="removeEditPill(this)">&times;</span>`;
    container.appendChild(pill);
    input.value = '';
}

function getPopupEditedTexts() {
    const texts = {};
    const arrayFields = ['capability', 'procedure', 'equipment', 'specialties'];
    for (const field of arrayFields) {
        const container = document.getElementById(`editpills_${field}`);
        if (container) {
            const pills = container.querySelectorAll('.field-pill');
            const items = Array.from(pills).map(p => p.getAttribute('data-value') || p.textContent.replace('×', '').trim());
            texts[field] = JSON.stringify(items);
        }
    }
    const descEl = document.getElementById('edit_description');
    if (descEl) texts.description = descEl.value;
    return texts;
}

async function doPopupRescore() {
    const btn = document.getElementById('btnRescore');
    btn.disabled = true;
    btn.textContent = 'Re-evaluating...';

    const texts = getPopupEditedTexts();
    try {
        const res = await fetch(`/api/facility/${popupFacilityId}/rescore`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ capability: popupSelectedCap, texts }),
        });
        popupRescoreResult = await res.json();
        showPopupDiff(popupRescoreResult);
    } catch (err) {
        alert('Error: ' + err.message);
    }
    btn.disabled = false;
    btn.textContent = 'Re-evaluate';
}

function showPopupDiff(result) {
    const container = document.getElementById('popupDiffContainer');
    const before = result.before;
    const after = result.after;

    const beforeCitations = (before.evidence_citations || []).map(c => `<div class="diff-citation-item">[${c.field}] ${escapeHtml(c.text)}</div>`).join('') || '<div class="diff-citation-item">None</div>';
    const afterCitations = (after.evidence_citations || []).map(c => `<div class="diff-citation-item">[${c.field}] ${escapeHtml(c.text)}</div>`).join('') || '<div class="diff-citation-item">None</div>';

    const changed = before.trust_level !== after.trust_level;

    container.innerHTML = `
        <div class="diff-header">Before / After ${changed ? '(Changed!)' : '(No change)'}</div>
        <div class="diff-comparison">
            <div class="diff-side">
                <div class="diff-side-title">Before</div>
                <div class="diff-trust-badge ${before.trust_level}">${TRUST_LABELS[before.trust_level] || before.trust_level}</div>
                <div style="font-size:11px;color:#888;margin-bottom:8px;">${before.match_count || 0} matches, ${(before.fields_matched || []).length} fields</div>
                <div class="diff-citations">${beforeCitations}</div>
            </div>
            <div class="diff-side">
                <div class="diff-side-title">After</div>
                <div class="diff-trust-badge ${after.trust_level}">${TRUST_LABELS[after.trust_level] || after.trust_level}</div>
                <div style="font-size:11px;color:#888;margin-bottom:8px;">${after.match_count || 0} matches, ${(after.fields_matched || []).length} fields</div>
                <div class="diff-citations">${afterCitations}</div>
            </div>
        </div>
        <div class="note-field">
            <label>Note (optional — why are you overriding?)</label>
            <textarea class="edit-field-textarea" id="overrideNote" placeholder="e.g., Verified by calling the facility directly"></textarea>
        </div>
        <button class="btn-confirm" id="btnConfirm" onclick="confirmPopupOverride()">Confirm & Save Override</button>
    `;
    container.classList.add('active');
}

async function confirmPopupOverride() {
    if (!popupRescoreResult) return;
    const btn = document.getElementById('btnConfirm');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    const note = document.getElementById('overrideNote').value || '';
    const texts = getPopupEditedTexts();

    try {
        const res = await fetch(`/api/facility/${popupFacilityId}/confirm-override`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                capability: popupSelectedCap,
                texts,
                old_result: popupRescoreResult.before,
                new_result: popupRescoreResult.after,
                note,
            }),
        });
        const data = await res.json();
        if (data.success) {
            // Refresh popup with updated data
            openFacilityPopup(popupFacilityId, popupSelectedCap);
        } else {
            alert('Error: ' + (data.error || 'Unknown'));
            btn.disabled = false;
            btn.textContent = 'Confirm & Save Override';
        }
    } catch (err) {
        alert('Error: ' + err.message);
        btn.disabled = false;
        btn.textContent = 'Confirm & Save Override';
    }
}

function closeFacilityPopup() {
    document.getElementById('facilityPopup').classList.remove('active');
    popupFacilityId = null;
    popupFacilityData = null;
    popupScores = [];
    popupSelectedCap = null;
    popupRescoreResult = null;
}

// Close on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.id === 'facilityPopup') closeFacilityPopup();
});

// ─── Search / Autocomplete ───────────────────────────────────────────────────
function setupSearch() {
    const input = document.getElementById('searchInput');
    const dropdown = document.getElementById('acDropdown');
    let debounceTimer;

    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        const q = input.value.trim();
        if (q.length < 2) { dropdown.classList.remove('active'); return; }
        dropdown.innerHTML = '<div class="ac-item"><div class="ac-item-text"><div class="ac-item-title" style="color:#666">Searching...</div></div></div>';
        dropdown.classList.add('active');
        debounceTimer = setTimeout(() => fetchSearch(q), 200);
    });

    input.addEventListener('blur', () => { setTimeout(() => dropdown.classList.remove('active'), 200); });
    input.addEventListener('keydown', (e) => { if (e.key === 'Escape') { dropdown.classList.remove('active'); input.blur(); } });
}

async function fetchSearch(q) {
    const dropdown = document.getElementById('acDropdown');
    const results = await fetch(`/api/search?q=${encodeURIComponent(q)}`).then(r => r.json());

    if (!results.length) {
        dropdown.innerHTML = '<div class="ac-item"><div class="ac-item-text"><div class="ac-item-title" style="color:#666">No results found</div></div></div>';
        return;
    }

    dropdown.innerHTML = results.map(r => `
        <div class="ac-item" onclick="handleSearchSelect('${r.type}', '${escapeAttr(r.title)}', '${r.id || ''}')">
            <div class="ac-item-icon ${r.type}">${r.type === 'facility' ? 'F' : r.type === 'capability' ? 'C' : 'R'}</div>
            <div class="ac-item-text">
                <div class="ac-item-title">${escapeHtml(r.title)}</div>
                <div class="ac-item-subtitle">${escapeHtml(r.subtitle || '')}</div>
            </div>
            <div class="ac-item-badge">${r.type.charAt(0).toUpperCase() + r.type.slice(1)}</div>
        </div>
    `).join('');
    dropdown.classList.add('active');
}

function handleSearchSelect(type, title, id) {
    document.getElementById('searchInput').value = '';
    document.getElementById('acDropdown').classList.remove('active');

    if (type === 'capability') {
        navigateTo('facilities', { capability: title });
    } else if (type === 'region') {
        navigateTo('facilities', { region: title });
    } else if (type === 'facility') {
        openFacilityPopup(id);
    }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function safeParseJSON(str, fallback) {
    if (!str) return fallback;
    try { return JSON.parse(str); } catch { return fallback; }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeAttr(text) {
    if (!text) return '';
    return text.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

function truncate(text, max) {
    if (!text) return '';
    return text.length > max ? text.slice(0, max) + '...' : text;
}

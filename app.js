// AI Travel Planner frontend. Everything from the API is rendered through
// markdown.js / escapeHtml, and the server looks up guides itself, so the page
// never sends guide text for anything except the PDF.
import { markdownToHtml, escapeHtml } from './markdown.js';

const API_URL = window.location.hostname.includes('app.github.dev')
    ? window.location.origin.replace('-3000.', '-8000.')
    : ['localhost', '127.0.0.1'].includes(window.location.hostname)
        ? 'http://localhost:8000'
        : 'https://ai-travel-planner-api-9d5f.onrender.com';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const $ = selector => document.querySelector(selector);

let current = null; // { destination, month, text, locations, tripId }

// Saved trips are stored as "Rome [May]"; show them as "Rome in May".
const tripName = stored => {
    const match = String(stored).match(/^(.*) \[(\w+)\]$/);
    return match && MONTHS.includes(match[2]) ? `${match[1]} in ${match[2]}` : String(stored);
};
let map = null;
let markers = [];

// --- Talking to the API --------------------------------------------------------------

async function api(path, options = {}) {
    const response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
    });
    if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        const message = typeof body.detail === 'string' ? body.detail
            : response.status === 422 ? 'Please choose a destination and month from the lists.'
            : 'Something went wrong. Please try again.';
        throw Object.assign(new Error(message), { status: response.status });
    }
    return response;
}

// --- Status line -------------------------------------------------------------------------

let slowTimer;
function setStatus(message = '', kind = '') {
    clearTimeout(slowTimer);
    const status = $('#status');
    status.textContent = message;
    status.className = `status${kind ? ` status--${kind}` : ''}`;
}

function busy(message) {
    setStatus(message, 'busy');
    // The free Render service sleeps when idle; say so if a request is slow.
    slowTimer = setTimeout(() => {
        $('#status').textContent = `${message} The server sleeps when it's quiet, so the first request can take up to a minute.`;
    }, 6000);
}

// --- Views ----------------------------------------------------------------------------------

function show(view) {
    $('#result').hidden = view !== 'result';
    $('#saved').hidden = view !== 'saved';
    $('#show-saved').setAttribute('aria-pressed', String(view === 'saved'));
}

function setUrl(params) {
    const query = new URLSearchParams(params).toString();
    history.replaceState(null, '', query ? `?${query}` : window.location.pathname);
}

function renderResult({ destination, month, text, locations, tripId = null, cached = false }) {
    current = { destination, month, text, locations, tripId };
    show('result');
    $('#result-kicker').textContent = tripId ? 'Saved trip' : 'Briefing';
    $('#result-title').textContent = month ? `${destination} in ${month}` : tripName(destination);
    $('#result-meta').textContent = [
        tripId ? 'From the shared trips' : cached ? 'From the cache' : 'Written just now',
        locations.length ? `${locations.length} place${locations.length === 1 ? '' : 's'} on the map` : null,
    ].filter(Boolean).join(' · ');

    const guide = $('#guide');
    guide.innerHTML = markdownToHtml(text, { headingOffset: 1 });
    for (const heading of guide.querySelectorAll('h3')) {
        if (heading.textContent.trim().toLowerCase() === 'sources') {
            heading.classList.add('sources');
            heading.nextElementSibling?.classList.add('sources');
        }
    }

    $('#save').hidden = Boolean(tripId);
    $('#save').disabled = false;
    $('#save').textContent = 'Save to trips';
    $('#back').hidden = !tripId;
    $('#answer').innerHTML = '';
    $('#question').value = '';

    renderMap(locations);
    $('#result').focus({ preventScroll: true });
    $('#result').scrollIntoView({ block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
}

function renderMap(locations) {
    const mapEl = $('#map');
    if (map) { map.remove(); map = null; }
    markers = [];
    mapEl.className = 'map';
    $('#places').innerHTML = locations.map((loc, i) => `
        <li><button type="button" data-place="${i}"><span class="n" aria-hidden="true">${i + 1}</span><span>${escapeHtml(loc.name)}</span></button></li>`).join('');
    $('#places-note').hidden = !locations.length;

    if (!locations.length || typeof L === 'undefined') {
        mapEl.classList.add('map--empty');
        mapEl.textContent = typeof L === 'undefined' ? 'The map could not load.' : 'No places to show on the map.';
        return;
    }
    mapEl.textContent = '';
    map = L.map(mapEl, { scrollWheelZoom: false });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
    }).addTo(map);
    markers = locations.map((loc, i) => L.marker([loc.lat, loc.lon], {
        icon: L.divIcon({ className: '', html: `<div class="pin"><span>${i + 1}</span></div>`, iconSize: [28, 28], iconAnchor: [14, 28], popupAnchor: [0, -26] }),
        title: loc.name,
        alt: loc.name,
    }).bindPopup(escapeHtml(loc.name)).addTo(map));
    if (locations.length > 1) map.fitBounds(L.featureGroup(markers).getBounds().pad(0.2));
    else map.setView([locations[0].lat, locations[0].lon], 13);
}

$('#places').addEventListener('click', event => {
    const button = event.target.closest('[data-place]');
    if (!button || !map) return;
    const i = Number(button.dataset.place);
    const loc = current.locations[i];
    map.setView([loc.lat, loc.lon], 15);
    markers[i].openPopup();
});

// --- Generating a briefing ---------------------------------------------------------------------

async function generate(destination, month) {
    const button = $('#generate');
    button.disabled = true;
    busy(`Researching ${destination} in ${month}…`);
    try {
        const data = await (await api('/api/generate-intel', { method: 'POST', body: JSON.stringify({ destination, month }) })).json();
        setStatus();
        renderResult({ destination: data.destination, month: data.month, text: data.intel, locations: data.locations || [], cached: data.cached });
        setUrl({ destination: data.destination, month: data.month });
    } catch (error) {
        setStatus(error.message, 'error');
    } finally {
        button.disabled = false;
    }
}

$('#ask-form').addEventListener('submit', event => {
    event.preventDefault();
    const destination = $('#destination').value;
    const month = $('#month').value;
    if (!destination) {
        setStatus('Choose a destination first.', 'error');
        $('#destination').focus();
        return;
    }
    generate(destination, month);
});

// --- Save, PDF, questions ---------------------------------------------------------------------------

$('#save').addEventListener('click', async () => {
    const button = $('#save');
    button.disabled = true;
    try {
        await api('/api/save-itinerary', { method: 'POST', body: JSON.stringify({ destination: current.destination, month: current.month }) });
        button.textContent = 'Saved';
        setStatus(`Saved ${current.destination} in ${current.month} to the shared trips.`);
    } catch (error) {
        button.disabled = false;
        setStatus(error.message, 'error');
    }
});

$('#pdf').addEventListener('click', async () => {
    const button = $('#pdf');
    button.disabled = true;
    try {
        const response = await api('/api/export-pdf', {
            method: 'POST',
            body: JSON.stringify({ destination: current.destination, month: current.month || '', guide_text: current.text }),
        });
        const url = URL.createObjectURL(await response.blob());
        const link = Object.assign(document.createElement('a'), {
            href: url,
            download: `${`${current.destination} ${current.month || ''}`.replace(/[\\/:*?"<>|]+/g, '').trim() || 'Travel guide'}.pdf`,
        });
        document.body.append(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    } catch (error) {
        setStatus(error.message, 'error');
    } finally {
        button.disabled = false;
    }
});

$('#chat-form').addEventListener('submit', async event => {
    event.preventDefault();
    const question = $('#question').value.trim();
    if (!question) return;
    const button = $('#ask');
    const answer = $('#answer');
    button.disabled = true;
    answer.textContent = 'Thinking…';
    // Only the question is sent; the server loads the guide itself.
    const which = current.tripId ? { trip_id: current.tripId } : { destination: current.destination, month: current.month };
    try {
        const data = await (await api('/api/chat', { method: 'POST', body: JSON.stringify({ ...which, user_query: question }) })).json();
        answer.innerHTML = `<p class="kicker">${escapeHtml(question)}</p>${markdownToHtml(data.response)}`;
    } catch (error) {
        answer.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});

// --- Saved trips ---------------------------------------------------------------------------------------

async function showSaved() {
    show('saved');
    setUrl({ trips: '1' });
    const list = $('#trips');
    list.innerHTML = '';
    busy('Loading saved trips…');
    try {
        const { trips } = await (await api('/api/itineraries')).json();
        setStatus();
        list.innerHTML = trips.length ? trips.map(trip => `
            <li><button type="button" data-trip="${Number(trip.id)}">
                <span class="trips__name">${escapeHtml(tripName(trip.destination))}</span>
                <span class="trips__date">${trip.created_at ? escapeHtml(new Date(trip.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })) : ''}</span>
            </button></li>`).join('')
            : '<li class="trips__empty">No saved trips yet. Write a briefing and save it.</li>';
        $('#saved').focus({ preventScroll: true });
    } catch (error) {
        setStatus(error.message, 'error');
    }
}

async function openTrip(id) {
    busy('Loading the trip…');
    try {
        const data = await (await api(`/api/itinerary/${Number(id)}`)).json();
        setStatus();
        renderResult({ destination: data.destination, month: '', text: data.guide_text, locations: data.locations || [], tripId: Number(id) });
        setUrl({ trip: id });
    } catch (error) {
        setStatus(error.message, 'error');
    }
}

$('#show-saved').addEventListener('click', showSaved);
$('#back').addEventListener('click', showSaved);
$('#trips').addEventListener('click', event => {
    const button = event.target.closest('[data-trip]');
    if (button) openTrip(button.dataset.trip);
});

// --- Theme ---------------------------------------------------------------------------------------------

const themeButton = $('#theme-toggle');
const isDark = () => document.documentElement.dataset.theme === 'dark'
    || (!document.documentElement.dataset.theme && matchMedia('(prefers-color-scheme: dark)').matches);
const syncTheme = () => {
    themeButton.textContent = isDark() ? 'Light mode' : 'Dark mode';
    themeButton.setAttribute('aria-pressed', String(isDark()));
};
themeButton.addEventListener('click', () => {
    const next = isDark() ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch {}
    syncTheme();
});
matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', syncTheme);
syncTheme();

// --- Start ------------------------------------------------------------------------------------------------

// Wake the server early; the free tier sleeps when idle.
fetch(`${API_URL}/health`).catch(() => {});

const params = new URLSearchParams(window.location.search);
$('#month').value = MONTHS[new Date().getMonth()];
if (params.get('trip')) {
    openTrip(params.get('trip'));
} else if (params.get('trips')) {
    showSaved();
} else if (params.get('destination') && MONTHS.includes(params.get('month'))) {
    const option = [...$('#destination').options].find(o => o.value === params.get('destination'));
    if (option) {
        $('#destination').value = option.value;
        $('#month').value = params.get('month');
        generate(option.value, params.get('month'));
    }
}

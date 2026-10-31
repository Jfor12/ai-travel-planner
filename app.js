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
const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

let current = null; // { destination, month, text, locations, tripId }
let trips = null;   // saved trips from the API: [{ id, city, month, created_at }], newest first

// Saved trips are stored as "Rome [May]"; split them into city and month.
const parseTrip = stored => {
    const match = String(stored).match(/^(.*) \[(\w+)\]$/);
    return match && MONTHS.includes(match[2]) ? { city: match[1], month: match[2] } : { city: String(stored), month: '' };
};
const tripName = stored => {
    const { city, month } = parseTrip(stored);
    return month ? `${city} in ${month}` : city;
};
let map = null;
let markers = [];

// --- Talking to the API --------------------------------------------------------------

async function api(path, options = {}) {
    let response;
    try {
        response = await fetch(`${API_URL}${path}`, {
            ...options,
            headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
        });
    } catch {
        throw Object.assign(new Error('Couldn’t reach the server. Check your connection and try again.'), { status: 0 });
    }
    if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        const message = typeof body.detail === 'string' ? body.detail
            : response.status === 422 ? 'The server couldn’t accept that request. Reload the page and try again.'
            : 'Something went wrong. Please try again.';
        throw Object.assign(new Error(message), { status: response.status });
    }
    return response;
}

// --- Status line, with optional actions (Try again, Browse saved trips) -----------------------------------

let stageTimers = [];
function setStatus(message = '', kind = '', actions = []) {
    stageTimers.forEach(clearTimeout);
    stageTimers = [];
    const status = $('#status');
    status.textContent = message;
    status.className = `status${kind ? ` status--${kind}` : ''}`;
    const box = $('#status-actions');
    box.innerHTML = '';
    box.hidden = !actions.length;
    for (const [label, run, quiet] of actions) {
        const button = Object.assign(document.createElement('button'), { type: 'button', className: `button${quiet ? ' button--quiet' : ''}`, textContent: label });
        button.addEventListener('click', run);
        box.append(button);
    }
}

// A request that can take a while: the message moves through its stages, and says the server may be waking up.
function busy(stages) {
    const [first, ...later] = Array.isArray(stages) ? stages : [[0, stages]];
    setStatus(first[1], 'busy');
    for (const [at, text] of later) stageTimers.push(setTimeout(() => { $('#status').textContent = text; }, at));
    stageTimers.push(setTimeout(() => {
        $('#status').textContent += ' The server sleeps when it’s quiet, so the first request can take up to a minute.';
    }, 7000));
}

function failed(error, retry) {
    if (error.status === 429) {
        setStatus('That’s the limit of new briefings for this hour. Briefings that already exist still open straight away, and saved trips are always available.', 'error',
            [['Browse saved trips', showSaved, true]]);
        return;
    }
    setStatus(error.message, 'error', retry ? [['Try again', retry, true]] : []);
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
    $('#existing').hidden = true;
    $('#result-kicker').textContent = tripId ? 'Saved trip' : 'Briefing';
    $('#result-title').textContent = month ? `${destination} in ${month}` : tripName(destination);
    $('#result-meta').textContent = [
        tripId ? 'From the shared trips' : cached ? 'Written earlier for this month' : 'Written just now',
        locations.length ? `${locations.length} place${locations.length === 1 ? '' : 's'} on the map` : null,
    ].filter(Boolean).join(' · ');

    const guide = $('#guide');
    guide.innerHTML = markdownToHtml(text, { headingOffset: 1, icons: true });
    for (const heading of guide.querySelectorAll('h3')) {
        if (heading.textContent.trim().toLowerCase() === 'sources') {
            heading.classList.add('sources');
            heading.nextElementSibling?.classList.add('sources');
        }
    }
    linkPlaces(guide, locations);

    $('#save').hidden = Boolean(tripId);
    $('#save').disabled = false;
    $('#save').textContent = 'Save to trips';
    $('#back').hidden = !tripId;
    $('#answer').innerHTML = '';
    $('#question').value = '';

    renderMap(locations);
    $('#result').focus({ preventScroll: true });
    $('#result').scrollIntoView({ block: 'start', behavior: reducedMotion() ? 'auto' : 'smooth' });
}

// Each place on the map gets its pin number next to its first mention in the briefing; tapping it shows the pin.
function linkPlaces(guide, locations) {
    const order = locations.map((loc, i) => ({ name: loc.name, i })).filter(p => p.name.length > 2).sort((a, b) => b.name.length - a.name.length);
    const escapeRe = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    for (const { name, i } of order) {
        const pattern = new RegExp(`(^|[^\\p{L}\\p{N}])(${escapeRe(name)})(?![\\p{L}\\p{N}])`, 'iu');
        const walker = document.createTreeWalker(guide, NodeFilter.SHOW_TEXT, {
            acceptNode: node => node.parentElement.closest('a, button, h3, .sources') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
        });
        let node;
        while ((node = walker.nextNode())) {
            const match = node.textContent.match(pattern);
            if (!match) continue;
            const start = match.index + match[1].length;
            const rest = node.splitText(start);
            rest.splitText(match[2].length);
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'place-ref';
            button.dataset.place = String(i);
            button.setAttribute('aria-label', `${rest.textContent}, pin ${i + 1}: show on the map`);
            button.innerHTML = `${escapeHtml(rest.textContent)}<span class="n" aria-hidden="true">${i + 1}</span>`;
            rest.replaceWith(button);
            break;
        }
    }
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

function showPlace(i) {
    if (!map) return;
    const loc = current.locations[i];
    markers.forEach((marker, n) => marker.getElement()?.querySelector('.pin')?.classList.toggle('pin--active', n === i));
    map.setView([loc.lat, loc.lon], 15);
    markers[i].openPopup();
    // On phones the map is below the text: bring it into view.
    const box = $('#map').getBoundingClientRect();
    if (box.top < 0 || box.bottom > innerHeight) $('#map').scrollIntoView({ block: 'center', behavior: reducedMotion() ? 'auto' : 'smooth' });
}

$('#places').addEventListener('click', event => {
    const button = event.target.closest('[data-place]');
    if (button) showPlace(Number(button.dataset.place));
});
$('#guide').addEventListener('click', event => {
    const button = event.target.closest('.place-ref');
    if (button) showPlace(Number(button.dataset.place));
});

// --- Generating a briefing ---------------------------------------------------------------------

async function generate(destination, month, { fresh = false } = {}) {
    const button = $('#generate');
    button.disabled = true;
    button.textContent = 'Writing…';
    $('#existing').hidden = true;
    busy([
        [0, `Looking for ${destination} in ${month}…`],
        [2500, `Searching the web for ${destination}: food, neighbourhoods, scams, transport and the weather…`],
        [12000, 'Writing the briefing and checking each section…'],
        [30000, 'Looking up the places on the map…'],
    ]);
    try {
        const data = await (await api('/api/generate-intel', { method: 'POST', body: JSON.stringify({ destination, month, fresh }) })).json();
        setStatus();
        renderResult({ destination: data.destination, month: data.month, text: data.intel, locations: data.locations || [], cached: data.cached });
        setUrl({ destination: data.destination, month: data.month });
    } catch (error) {
        failed(error, () => generate(destination, month, { fresh }));
    } finally {
        button.disabled = false;
        button.textContent = 'Write the briefing';
    }
}

async function loadTrips() {
    const { trips: list } = await (await api('/api/itineraries')).json();
    trips = list.map(trip => ({ id: Number(trip.id), ...parseTrip(trip.destination), created_at: trip.created_at }));
    return trips;
}

// The newest saved trip for this city and month, if there is one. A slow server never holds up a new briefing.
async function savedTripFor(destination, month) {
    if (!trips) {
        try { await Promise.race([loadTrips(), new Promise((_, reject) => setTimeout(reject, 4000))]); } catch { return null; }
    }
    return trips.find(t => t.city.toLowerCase() === destination.toLowerCase() && t.month === month) || null;
}

$('#ask-form').addEventListener('submit', async event => {
    event.preventDefault();
    const destination = $('#destination').value;
    const month = $('#month').value;
    if (!destination) {
        setStatus('Choose a destination first.', 'error');
        $('#destination').focus();
        return;
    }
    $('#generate').disabled = true;
    const existing = await savedTripFor(destination, month);
    $('#generate').disabled = false;
    if (!existing) return generate(destination, month);
    setStatus();
    $('#existing-text').textContent = `A briefing for ${destination} in ${month} already exists. Open it, or write a fresh one?`;
    $('#existing').hidden = false;
    $('#existing-open').onclick = () => { $('#existing').hidden = true; openTrip(existing.id); };
    $('#existing-fresh').onclick = () => generate(destination, month, { fresh: true });
    $('#existing-open').focus();
});

// --- Save, PDF, questions ---------------------------------------------------------------------------

$('#save').addEventListener('click', async () => {
    // Feedback goes on the button itself, which is where the visitor is looking.
    const button = $('#save');
    button.disabled = true;
    button.textContent = 'Saving…';
    try {
        await api('/api/save-itinerary', { method: 'POST', body: JSON.stringify({ destination: current.destination, month: current.month }) });
        button.textContent = 'Saved to trips';
        trips = null; // reload the list next time
        setStatus(`Saved ${current.destination} in ${current.month} to the shared trips.`);
    } catch (error) {
        button.disabled = false;
        button.textContent = 'Couldn’t save. Try again';
        setStatus(error.message, 'error');
    }
});

$('#pdf').addEventListener('click', async () => {
    const button = $('#pdf');
    button.disabled = true;
    button.textContent = 'Making the PDF…';
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
        button.textContent = 'Download PDF';
    }
});

$('#chat-form').addEventListener('submit', async event => {
    event.preventDefault();
    const question = $('#question').value.trim();
    if (!question) return;
    const button = $('#ask');
    const answer = $('#answer');
    button.disabled = true;
    answer.classList.remove('chat__answer--error');
    answer.innerHTML = '<p class="status status--busy">Thinking…</p>';
    // Only the question is sent; the server loads the guide itself.
    const which = current.tripId ? { trip_id: current.tripId } : { destination: current.destination, month: current.month };
    try {
        const data = await (await api('/api/chat', { method: 'POST', body: JSON.stringify({ ...which, user_query: question }) })).json();
        answer.innerHTML = `<p class="kicker">${escapeHtml(question)}</p>${markdownToHtml(data.response)}`;
    } catch (error) {
        answer.classList.add('chat__answer--error');
        answer.textContent = error.status === 429 ? 'That’s the limit of questions for this hour. Please try again later.' : error.message;
    } finally {
        button.disabled = false;
    }
});

// --- Saved trips: one card per city, a chip per month (newest briefing for each), and a filter --------------

function renderTrips() {
    const query = $('#trip-filter').value.trim().toLowerCase();
    const newest = new Map();
    for (const trip of trips) {
        const key = `${trip.city.toLowerCase()}|${trip.month}`;
        if (!newest.has(key)) newest.set(key, trip); // the list is newest first
    }
    const cities = new Map();
    for (const trip of newest.values()) {
        const matches = !query || trip.city.toLowerCase().includes(query) || trip.month.toLowerCase().startsWith(query);
        if (!matches) continue;
        if (!cities.has(trip.city)) cities.set(trip.city, []);
        cities.get(trip.city).push(trip);
    }
    const groups = [...cities.entries()].sort(([a], [b]) => a.localeCompare(b));
    const count = groups.reduce((n, [, list]) => n + list.length, 0);
    $('#trip-count').textContent = !trips.length ? ''
        : query ? `${count} briefing${count === 1 ? '' : 's'} match “${$('#trip-filter').value.trim()}”.`
        : `${count} briefings for ${groups.length} cities.`;
    $('#trips').innerHTML = !trips.length ? '<li class="trips__empty">No saved trips yet. Write a briefing and save it.</li>'
        : !groups.length ? '<li class="trips__empty">No saved trips match that. Try a city or a month.</li>'
        : groups.map(([city, list]) => `
            <li class="trip">
                <h3 class="trips__name">${escapeHtml(city)}</h3>
                <ul class="chips" aria-label="${escapeHtml(city)}: months">
                    ${list.sort((a, b) => MONTHS.indexOf(a.month) - MONTHS.indexOf(b.month)).map(trip => `
                    <li><button type="button" class="chip" data-trip="${trip.id}" aria-label="${escapeHtml(tripName(`${trip.city} [${trip.month}]`))}"${trip.created_at ? ` title="Saved ${escapeHtml(new Date(trip.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }))}"` : ''}>${escapeHtml(trip.month || 'Briefing')}</button></li>`).join('')}
                </ul>
            </li>`).join('');
}

async function showSaved() {
    show('saved');
    setUrl({ trips: '1' });
    $('#existing').hidden = true;
    // Bring the list into view and say where we are, on phones too (it opens below the form).
    $('#saved').scrollIntoView({ block: 'start', behavior: reducedMotion() ? 'auto' : 'smooth' });
    $('#saved-title').focus({ preventScroll: true });
    if (!trips) {
        $('#trips').innerHTML = '';
        $('#trip-count').textContent = '';
        busy('Loading saved trips…');
        try {
            await loadTrips();
            setStatus();
        } catch (error) {
            failed(error, showSaved);
            return;
        }
    }
    renderTrips();
}

$('#trip-filter').addEventListener('input', () => { if (trips) renderTrips(); });

async function openTrip(id) {
    busy('Opening the trip…');
    try {
        const data = await (await api(`/api/itinerary/${Number(id)}`)).json();
        setStatus();
        renderResult({ destination: data.destination, month: '', text: data.guide_text, locations: data.locations || [], tripId: Number(id) });
        setUrl({ trip: id });
    } catch (error) {
        failed(error, () => openTrip(id));
    }
}

$('#show-saved').addEventListener('click', showSaved);
$('#back').addEventListener('click', showSaved);
$('#trips').addEventListener('click', event => {
    const button = event.target.closest('[data-trip]');
    if (button) openTrip(button.dataset.trip);
});

// --- Theme: the button shows the theme on screen; pressed means dark ------------------------------------------

const themeButton = $('#theme-toggle');
const isDark = () => document.documentElement.dataset.theme === 'dark'
    || (!document.documentElement.dataset.theme && matchMedia('(prefers-color-scheme: dark)').matches);
const syncTheme = () => {
    const dark = isDark();
    themeButton.setAttribute('aria-pressed', String(dark));
    themeButton.title = dark ? 'Dark mode is on' : 'Dark mode is off';
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

// Turns a guide's Markdown into safe HTML. Everything is escaped first, so
// nothing in a guide or chat reply can become markup or script; only the
// formatting below is added back.

export const escapeHtml = value => String(value ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

const PAGE_BREAK = /\(?-{3}\s*page break\s*-{3}\)?/i;
const RULE = /^([-*_])(\s*\1){2,}$/; // "---": older guides end with one before the coordinates

// Each section's icon comes from its name, so older guides (with their own emoji, and a warning sign on
// Logistics) and newer ones look the same. The model's emoji, if any, is dropped.
const SECTION_ICONS = [
    [/\b(food|gastronomy|eat)\b/i, '🍝'],
    [/neighbo/i, '🏘️'],
    [/logistics|getting around/i, '🧭'],
    [/scam/i, '🛡️'],
    [/weather|season|crowd/i, '🌦️'],
];
const LEADING_SYMBOLS = /^[^\p{L}\p{N}(]+/u;

function sectionHeading(text) {
    const name = String(text).replace(LEADING_SYMBOLS, '').replace(/\bNeighborhood/g, 'Neighbourhood').trim();
    const icon = SECTION_ICONS.find(([pattern]) => pattern.test(name))?.[1];
    return icon ? `<span class="h-icon" aria-hidden="true">${icon}</span><span>${inline(name)}</span>` : inline(name);
}

function inline(text) {
    const links = [];
    // Links first, from the raw text, so the URL can be checked before escaping.
    let out = String(text).replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, label, url) => {
        links.push(`<a href="${escapeHtml(url)}" rel="noopener noreferrer" target="_blank">${escapeHtml(label)}</a>`);
        return `\u0000${links.length - 1}\u0000`;
    });
    out = escapeHtml(out)
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.+?)__/g, '<strong>$1</strong>')
        .replace(/(^|[^*\w])\*(?!\s)([^*]+?)\*(?!\*)/g, '$1<em>$2</em>');
    return out.replace(/\u0000(\d+)\u0000/g, (_, i) => links[Number(i)]);
}

// Returns HTML for the readable part of a guide (the map coordinates block is left out).
export function markdownToHtml(markdown, { headingOffset = 0, icons = false } = {}) {
    const body = String(markdown ?? '').split(PAGE_BREAK)[0];
    const out = [];
    let list = null;
    const flush = () => { if (list) { out.push(`<ul>${list.join('')}</ul>`); list = null; } };
    for (const raw of body.split('\n')) {
        const line = raw.trim();
        if (/^#{1,6}\s*coordinates\b/i.test(line)) break;
        const item = line.match(/^[*-]\s+(.*)$/);
        if (item) {
            const nested = /^\s{2,}/.test(raw); // an indented bullet belongs to the item above
            (list = list || []).push(`<li${nested ? ' class="sub"' : ''}>${inline(item[1])}</li>`);
            continue;
        }
        flush();
        if (!line || RULE.test(line)) continue;
        const heading = line.match(/^(#{1,4})\s+(.*)$/);
        if (heading) {
            const level = Math.min(6, heading[1].length + headingOffset);
            out.push(`<h${level}>${icons && heading[1].length === 2 ? sectionHeading(heading[2]) : inline(heading[2])}</h${level}>`);
        } else {
            out.push(`<p>${inline(line)}</p>`);
        }
    }
    flush();
    return out.join('');
}

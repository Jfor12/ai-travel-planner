// Run with: npm test (Node 20+)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { markdownToHtml, escapeHtml } from '../markdown.js';

test('script and event-handler markup is escaped', () => {
    const html = markdownToHtml('## Food <script>alert(1)</script>\n* **Dish:** <img src=x onerror="alert(1)">');
    assert.doesNotMatch(html, /<script|<img/);
    assert.match(html, /&lt;img src=x onerror=&quot;alert\(1\)&quot;&gt;/);
});

test('only http(s) links become links, and label and URL are escaped', () => {
    const html = markdownToHtml('* [ok](https://example.com/a?b=1&c=2)\n* [bad](javascript:alert(1))\n* [x"y](https://e.com/"onmouseover=alert(1))');
    assert.match(html, /<a href="https:\/\/example\.com\/a\?b=1&amp;c=2" rel="noopener noreferrer" target="_blank">ok<\/a>/);
    assert.doesNotMatch(html, /href="javascript/);
    assert.doesNotMatch(html, /href="[^"]*"onmouseover/);
});

test('guide structure: headings, lists, bold and italics', () => {
    const html = markdownToHtml('## Gastronomy\n* **Croissant:** Flaky, *best early*.\n* **Steak frites:** Classic.\n\nPlain paragraph.', { headingOffset: 1 });
    assert.equal(html, '<h3>Gastronomy</h3><ul><li><strong>Croissant:</strong> Flaky, <em>best early</em>.</li><li><strong>Steak frites:</strong> Classic.</li></ul><p>Plain paragraph.</p>');
});

test('the coordinates block is not shown', () => {
    for (const md of ['## A\n* x\n\n(---PAGE BREAK---)\n### COORDINATES\nX | 1 | 2', '## A\n* x\n### COORDINATES\nX | 1 | 2']) {
        assert.equal(markdownToHtml(md), '<h2>A</h2><ul><li>x</li></ul>');
    }
});

test('escapeHtml handles null and quotes', () => {
    assert.equal(escapeHtml(null), '');
    assert.equal(escapeHtml(`<a href='x'>"`), '&lt;a href=&#39;x&#39;&gt;&quot;');
});

test('indented bullets are marked as sub-points', () => {
    const html = markdownToHtml('* **Safety:**\n  * **Pickpockets:** Front pockets.\n* **Tips:** Round up.');
    assert.equal(html, '<ul><li><strong>Safety:</strong></li><li class="sub"><strong>Pickpockets:</strong> Front pockets.</li><li><strong>Tips:</strong> Round up.</li></ul>');
});

test('stray rules are dropped; section icons are consistent and the emoji gets its own span', () => {
    const html = markdownToHtml('## ⚠️ Logistics\n* x\n\n## 🍝 Gastronomy (What to order)\n* y\n\n## Neighborhoods\n* z\n\n---\n### COORDINATES\nA | 1 | 2', { headingOffset: 1, icons: true });
    assert.doesNotMatch(html, /---|⚠/);
    assert.match(html, /<h3><span class="h-icon" aria-hidden="true">🧭<\/span><span>Logistics<\/span><\/h3>/);
    assert.match(html, /<h3><span class="h-icon" aria-hidden="true">🍝<\/span><span>Gastronomy \(What to order\)<\/span><\/h3>/);
    assert.match(html, /<span>Neighbourhoods<\/span>/);
    assert.match(markdownToHtml('## Weather and crowds (May)', { icons: true }), /🌦️/);
    assert.equal(markdownToHtml('## Sources\n* [a](https://a.com)', { icons: true }), '<h2>Sources</h2><ul><li><a href="https://a.com" rel="noopener noreferrer" target="_blank">a</a></li></ul>');
});

test('hyphenated names are left alone', () => {
    assert.equal(markdownToHtml('* **Canal Saint-Martin:** A walk-up bar.'), '<ul><li><strong>Canal Saint-Martin:</strong> A walk-up bar.</li></ul>');
});

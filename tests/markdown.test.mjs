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

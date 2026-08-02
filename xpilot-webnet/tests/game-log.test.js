'use strict';
// Tests for the in-game chat/log module (issue #32).
//
// game-log.js provides:
//   * LogBuffer      — ordered, de-duplicated, bounded log rows (DOM-free)
//   * formatEvent    — pure rendering of raw events into human-readable text
//   * formatTimestamp
//   * GameLogUI      — thin DOM binding (requires document; not exercised here)
//
// Run with:  node --test tests/
const { test } = require('node:test');
const assert = require('node:assert');

const {
  LogBuffer,
  formatEvent,
  formatTimestamp,
} = require('../game-log.js');

// ── formatEvent ─────────────────────────────────────────────────────────
test('formats join/leave events', () => {
  assert.strictEqual(
    formatEvent({ event: 'join', id: 'p_abc', name: 'Nova' }),
    'Nova joined the game',
  );
  assert.strictEqual(
    formatEvent({ event: 'leave', id: 'p_abc', name: 'Nova' }),
    'Nova left the game',
  );
});

test('formats death events with and without a killer', () => {
  assert.strictEqual(
    formatEvent({ event: 'death', id: 'p_a', name: 'A', killer: 'p_b', killerName: 'B' }),
    'A was destroyed by B',
  );
  assert.strictEqual(
    formatEvent({ event: 'death', id: 'p_a', name: 'A', killer: '' }),
    'A was destroyed',
  );
  assert.strictEqual(
    formatEvent({ event: 'death', id: 'p_a', name: 'A' }),
    'A was destroyed',
  );
});

test('formats my own death from my perspective', () => {
  const ev = { event: 'death', id: 'me', name: 'Me', killer: 'p_b', killerName: 'B' };
  assert.strictEqual(formatEvent(ev, 'me'), 'You were destroyed by B');
  assert.strictEqual(
    formatEvent({ event: 'death', id: 'me', name: 'Me' }, 'me'),
    'You were destroyed',
  );
});

test('formats chat events', () => {
  assert.strictEqual(
    formatEvent({ event: 'chat', id: 'p_a', name: 'A', text: 'hello' }),
    'A: hello',
  );
});

test('formats pickup and announce events', () => {
  assert.strictEqual(
    formatEvent({ event: 'pickup', id: 'p_a', name: 'A', item: 'shield' }),
    'A picked up shield',
  );
  assert.strictEqual(
    formatEvent({ event: 'announce', text: 'Round over' }),
    'Round over',
  );
});

// ── LogBuffer ordering / dedup / bounds ─────────────────────────────────
test('appends local (unsequenced) events in arrival order', () => {
  const buf = new LogBuffer({ maxMessages: 10 });
  assert.deepStrictEqual(buf.push({ event: 'chat', id: 'a', name: 'A', text: 'hi' }), [buf.rows[0]]);
  buf.push({ event: 'chat', id: 'b', name: 'B', text: 'yo' });
  assert.strictEqual(buf.count(), 2);
  assert.strictEqual(buf.rows[0].text, 'A: hi');
  assert.strictEqual(buf.rows[1].text, 'B: yo');
});

test('drops duplicate/stale sequenced events', () => {
  const buf = new LogBuffer({ maxMessages: 10 });
  buf.push({ event: 'join', seq: 1, id: 'a', name: 'A' });
  assert.strictEqual(buf.count(), 1);
  // Duplicate of seq 1 is ignored.
  assert.strictEqual(buf.push({ event: 'death', seq: 1, id: 'b', name: 'B' }), null);
  assert.strictEqual(buf.count(), 1);
});

test('orders out-of-order events once the gap is filled', () => {
  const buf = new LogBuffer({ maxMessages: 10 });
  buf.push({ event: 'death', seq: 3, id: 'b', name: 'B' });   // gap: seqs 1,2 missing
  assert.strictEqual(buf.count(), 0);
  buf.push({ event: 'join', seq: 1, id: 'a', name: 'A' });
  buf.push({ event: 'join', seq: 2, id: 'c', name: 'C' });
  // Draining applies 2 and 3 in order.
  assert.strictEqual(buf.count(), 3);
  assert.deepStrictEqual(
    buf.rows.map((r) => r.seq),
    [1, 2, 3],
  );
});

test('bounded by maxMessages (newest kept)', () => {
  const buf = new LogBuffer({ maxMessages: 3 });
  for (let i = 1; i <= 6; i++) buf.push({ event: 'chat', seq: i, id: 'a', name: 'A', text: String(i) });
  assert.strictEqual(buf.count(), 3);
  assert.deepStrictEqual(buf.rows.map((r) => r.seq), [4, 5, 6]);
});

test('loadHistory applies a bounded replay in seq order', () => {
  const buf = new LogBuffer({ maxMessages: 20 });
  buf.loadHistory([
    { event: 'join', seq: 1, id: 'a', name: 'A' },
    { event: 'death', seq: 3, id: 'b', name: 'B', killer: 'a', killerName: 'A' },
    { event: 'join', seq: 2, id: 'c', name: 'C' },
  ]);
  assert.strictEqual(buf.count(), 3);
  assert.deepStrictEqual(buf.rows.map((r) => r.seq), [1, 2, 3]);
  assert.strictEqual(buf.rows[2].text, 'B was destroyed by A');
  // The next live event continues contiguously after the history.
  buf.push({ event: 'chat', seq: 4, id: 'a', name: 'A', text: 'welcome' });
  assert.strictEqual(buf.count(), 4);
  assert.strictEqual(buf.rows[3].seq, 4);
});

test('setMaxMessages trims to the new bound', () => {
  const buf = new LogBuffer({ maxMessages: 5 });
  for (let i = 1; i <= 5; i++) buf.push({ event: 'chat', seq: i, id: 'a', name: 'A', text: String(i) });
  buf.setMaxMessages(2);
  assert.strictEqual(buf.count(), 2);
  assert.deepStrictEqual(buf.rows.map((r) => r.seq), [4, 5]);
});

test('clear resets rows and sequence tracking', () => {
  const buf = new LogBuffer({ maxMessages: 10 });
  buf.push({ event: 'join', seq: 1, id: 'a', name: 'A' });
  buf.clear();
  assert.strictEqual(buf.count(), 0);
  // A new server session can start over from seq 1.
  buf.push({ event: 'join', seq: 1, id: 'a', name: 'A' });
  assert.strictEqual(buf.count(), 1);
});

test('formatTimestamp renders HH:MM:SS and tolerates bad input', () => {
  assert.match(formatTimestamp(new Date(0).getTime()), /^\d\d:\d\d:\d\d$/);
  // null/undefined means "no timestamp" and falls back to the current time.
  assert.match(formatTimestamp(null), /^\d\d:\d\d:\d\d$/);
  assert.strictEqual(formatTimestamp('not-a-date'), '');
});

const test = require('node:test');
const assert = require('node:assert/strict');
const { createPickup, applyBulletDamageToPickup, getPickupRespawnKind, getPickupBlastRadius, getPickupExplosionDelay, FUEL_CELL_BLAST_RADIUS } = require('../pickup-system.js');

test('fragile pickups are destroyed in one hit', () => {
  const pickup = createPickup('score_mult', { x: 100, y: 100, active: true });
  const result = applyBulletDamageToPickup(pickup, 1, { consumeOnImpact: true });
  assert.equal(result.destroyed, true);
  assert.equal(result.shouldConsumeBullet, true);
  assert.equal(pickup.active, false);
  assert.equal(pickup.hp, 0);
});

test('shield pickups survive multiple hits', () => {
  const pickup = createPickup('shield', { x: 100, y: 100, active: true });
  const first = applyBulletDamageToPickup(pickup, 1, { consumeOnImpact: true });
  assert.equal(first.destroyed, false);
  assert.equal(pickup.hp, 2);
  const second = applyBulletDamageToPickup(pickup, 1, { consumeOnImpact: true });
  assert.equal(second.destroyed, false);
  assert.equal(pickup.hp, 1);
  const third = applyBulletDamageToPickup(pickup, 1, { consumeOnImpact: true });
  assert.equal(third.destroyed, true);
  assert.equal(pickup.active, false);
  assert.equal(pickup.hp, 0);
});

test('durable pickups need multiple hits', () => {
  const pickup = createPickup('fuel_cell', { x: 120, y: 120, active: true });
  const first = applyBulletDamageToPickup(pickup, 1, { consumeOnImpact: true });
  const second = applyBulletDamageToPickup(pickup, 2, { consumeOnImpact: true });
  assert.equal(first.destroyed, false);
  assert.equal(second.destroyed, true);
  assert.equal(pickup.hp, 0);
});

test('fuel cells can be marked for respawn and expose a blast radius', () => {
  const pickup = createPickup('fuel_cell', { x: 120, y: 120, active: true });
  assert.equal(getPickupRespawnKind(pickup), 'fuel_cell');
  assert.equal(getPickupBlastRadius(pickup), FUEL_CELL_BLAST_RADIUS);
  assert.ok(FUEL_CELL_BLAST_RADIUS < 140, 'fuel cell blast radius should be smaller than before');
  assert.equal(getPickupExplosionDelay(pickup), 1.4);
});

test('fuel cell blast radius can be overridden per pickup', () => {
  const pickup = createPickup('fuel_cell', { x: 120, y: 120, active: true, blastRadius: 60 });
  assert.equal(getPickupBlastRadius(pickup), 60);
});

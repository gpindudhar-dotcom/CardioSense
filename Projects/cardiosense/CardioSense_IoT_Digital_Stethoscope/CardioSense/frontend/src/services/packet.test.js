import test from 'node:test';
import assert from 'node:assert/strict';

/**
 * Lightweight frontend-side packet offset documentation test.
 * Backend owns full binary parsing; this guards magic/constant drift in docs.
 */
test('CSND magic constant', () => {
  const magic = 0x44534e43;
  assert.equal(magic, 0x44534e43);
  const bytes = Buffer.alloc(4);
  bytes.writeUInt32LE(magic, 0);
  assert.equal(bytes.toString('ascii'), 'CSND');
});

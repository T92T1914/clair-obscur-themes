import assert from 'node:assert/strict';
import { test } from 'node:test';
import { assertRenderedFace } from './font-evidence.mjs';

test('the expected face must supply rendered glyphs itself', () => {
  const fonts = [
    { postScriptName: 'SegoeUI', glyphCount: 12 },
    { postScriptName: 'Inter-Regular', glyphCount: 0 },
  ];
  assert.throws(() => assertRenderedFace(fonts, 'Inter-Regular'), /Expected positive rendered glyphs/);
  assert.doesNotThrow(() => assertRenderedFace([
    { postScriptName: 'Inter-Regular', glyphCount: 12 },
  ], 'Inter-Regular'));
});

test('missing, empty and invalid glyph evidence cannot pass', () => {
  for (const fonts of [undefined, null, [], {}, [null],
    [{ postScriptName: 'Inter-Regular' }],
    [{ postScriptName: 'Inter-Regular', glyphCount: '12' }],
    [{ postScriptName: 'Inter-Regular', glyphCount: -1 }],
    [{ postScriptName: 'Inter-Regular', glyphCount: 0.5 }]]) {
    assert.throws(() => assertRenderedFace(fonts, 'Inter-Regular'), { name: 'AssertionError' });
  }
});

test('regular or bold glyphs do not establish a genuine italic face', () => {
  assert.throws(() => assertRenderedFace([
    { postScriptName: 'Inter-Regular', glyphCount: 9 },
    { postScriptName: 'Inter-Bold', glyphCount: 3 },
  ], 'Inter-BoldItalic'), /Expected positive rendered glyphs/);
  assert.doesNotThrow(() => assertRenderedFace([
    { postScriptName: 'Inter-BoldItalic', glyphCount: 12 },
    { postScriptName: 'SegoeUIEmoji', glyphCount: 1 },
  ], 'Inter-BoldItalic'));
});

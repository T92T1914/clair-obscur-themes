import assert from 'node:assert/strict';

export function assertRenderedFace(fonts, postScriptName) {
  assert.ok(Array.isArray(fonts) && fonts.length > 0, 'Rendered font evidence is missing');
  assert.ok(fonts.some(font => font?.postScriptName === postScriptName
    && Number.isInteger(font.glyphCount) && font.glyphCount > 0),
  `Expected positive rendered glyphs from ${postScriptName}: ${JSON.stringify(fonts)}`);
}

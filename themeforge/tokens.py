import json
import re
from pathlib import Path

ROLES = frozenset('canvas panel text muted divider control hover selected border accent on_accent focus success warning error code disabled'.split())

def rgb(hex_color):
    if not isinstance(hex_color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', hex_color):
        raise ValueError(f'Expected an opaque sRGB hex color: {hex_color!r}')
    return tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))

def luminance(color):
    channels = [n/255 for n in rgb(color)]
    linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in channels]
    return sum(v*w for v,w in zip(linear, (.2126, .7152, .0722)))

def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high+.05)/(low+.05)

def validate(document):
    if document.get('schema_version') != 1 or set(document.get('themes', {})) != {'Clair', 'Obscur'}:
        raise ValueError('Expected schema 1 with Clair and Obscur')
    if not re.fullmatch(r'\d+\.\d+\.\d+', document.get('version', '')):
        raise ValueError('Expected a numeric three-part version')
    checks = []
    for name, values in document['themes'].items():
        if set(values) != ROLES:
            raise ValueError(f'{name}: missing or unexpected token roles')
        for value in values.values():
            rgb(value)
        pairs = [(fg, bg, 4.5) for fg in ('text','muted') for bg in ('canvas','panel','control','hover','selected','code')]
        pairs += [(fg, 'panel', 4.5) for fg in ('accent','success','warning','error')]
        pairs += [('on_accent','accent',4.5)]
        pairs += [(fg,bg,3) for fg in ('focus','border') for bg in ('canvas','panel','control','hover','selected')]
        for fg,bg,minimum in pairs:
            ratio=contrast(values[fg],values[bg])
            if ratio < minimum:
                raise ValueError(f'{name}: {fg} on {bg} is {ratio:.2f}:1, below {minimum}:1')
            checks.append({'theme':name,'foreground':fg,'background':bg,'ratio':round(ratio,4),'minimum':minimum})
    return checks

def load(path: Path):
    document=json.loads(path.read_text(encoding='utf-8'))
    validate(document)
    return document

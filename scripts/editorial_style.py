"""Small, reusable style tokens; legacy themes remain unchanged."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PALETTES = {p['id']: p for p in json.loads((ROOT/'assets/editorial-palettes.json').read_text())}

def palette(name='warm'):
    key = name.removeprefix('editorial-')
    if key not in PALETTES:
        raise ValueError('unknown editorial theme: ' + name)
    return dict(PALETTES[key])

def vector_themes():
    return {'editorial-'+k: dict(bg=p['bg'], panel=p['bg'], ink=p['ink'],
        muted=p['muted'], line=p['line'], accent=p['accent'], teal=p['muted'],
        amber=p['accent'], red=p['ink'], tint=p['tint'], tint2=p['outer'])
        for k, p in PALETTES.items()}

def mpl_style(name='warm'):
    from matplotlib import font_manager
    p = palette(name)
    candidates = ['/System/Library/Fonts/STHeiti Light.ttc',
        '/System/Library/Fonts/Supplemental/Songti.ttc']
    for path in candidates:
        if Path(path).exists():
            font_manager.fontManager.addfont(path)
    available = {f.name for f in font_manager.fontManager.ttflist}
    body = next((x for x in ['Heiti SC','Heiti TC','PingFang SC','Noto Sans CJK SC','Microsoft YaHei'] if x in available), 'DejaVu Sans')
    heading = next((x for x in ['Songti SC','Noto Serif CJK SC',body] if x in available), body)
    return p, heading, {'font.family':body,'font.size':11,'axes.unicode_minus':False,
        'svg.fonttype':'none','pdf.fonttype':42,'figure.facecolor':p['bg'],
        'axes.facecolor':p['bg'],'text.color':p['ink'],'axes.labelcolor':p['muted'],
        'xtick.color':p['muted'],'ytick.color':p['muted'],'axes.edgecolor':p['line'],
        'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,
        'grid.color':p['line'],'grid.linewidth':.5,'legend.frameon':False,
        'savefig.facecolor':p['bg']}

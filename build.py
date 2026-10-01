"""Builds the RezaMDI portfolio site into dist/.

Reads content/settings.json and content/photos/*.json (both edited through /admin),
makes web-sized copies of every photo, and writes the home page plus one page per category.
Run locally with:  python3 build.py
"""
import colorsys
import datetime
import glob
import hashlib
import html
import json
import os
import re
import shutil

from PIL import Image, ImageOps, ImageDraw, ImageFont

try:  # lets iPhone HEIC uploads work when pillow-heif is installed (it is on Netlify)
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, 'dist')
E = html.escape


def rp(*p):
    return os.path.join(ROOT, *p)


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', str(s).lower()).strip('-') or 'photo'


def inline(md):
    """Escape text and turn *word* into <em>word</em>."""
    return re.sub(r'\*(.+?)\*', r'<em>\1</em>', E(md or ''))


# ---------------------------------------------------------------- content
S = json.load(open(rp('content', 'settings.json'), encoding='utf-8'))
CATS = [c for c in S.get('categories', []) if c.get('key')]
CAT_NAME = {c['key']: c.get('name') or c['key'].title() for c in CATS}

photos = []
for f in sorted(glob.glob(rp('content', 'photos', '*.json'))):
    try:
        d = json.load(open(f, encoding='utf-8'))
    except Exception as e:
        print(f'! skipped {os.path.basename(f)}: {e}')
        continue
    if not d.get('image') or d.get('category') not in CAT_NAME or d.get('hidden'):
        continue
    d.setdefault('title', os.path.splitext(os.path.basename(f))[0].replace('-', ' ').capitalize())
    d['order'] = float(d.get('order') or 100)
    photos.append(d)

# ---------------------------------------------------------------- images
if os.path.isdir(DIST):
    shutil.rmtree(DIST)
for d in ('img', 'thumb'):
    os.makedirs(os.path.join(DIST, d), exist_ok=True)

_done = {}


def exif_text(im):
    try:
        e = im.getexif()
        ex = e.get_ifd(0x8769)
        model = (e.get(272) or '').strip().replace('Canon ', '')
        if not model:
            return ''
        parts = [model]
        if ex.get(0x920A):
            parts.append(f'{float(ex[0x920A]):g}mm')
        if ex.get(0x829D):
            parts.append(f'f/{float(ex[0x829D]):g}')
        t = ex.get(0x829A)
        if t and float(t) < 1:
            parts.append(f'1/{round(1 / float(t))}')
        if ex.get(0x8827):
            parts.append(f'ISO {ex[0x8827]}')
        return ' · '.join(parts)
    except Exception:
        return ''


def process(path):
    """Make img/ (1800px) and thumb/ (900px) versions. Returns (id, w, h, camera, colour)."""
    if path in _done:
        return _done[path]
    src = rp(path.lstrip('/'))
    if not os.path.exists(src):
        print(f'! missing image {path}')
        _done[path] = None
        return None
    stem = slug(os.path.splitext(os.path.basename(src))[0])[:60]
    pid = f'{stem}-{hashlib.md5(path.encode()).hexdigest()[:5]}'
    im = Image.open(src)
    cam = exif_text(im)
    im = ImageOps.exif_transpose(im).convert('RGB')
    big = im.copy()
    big.thumbnail((1800, 1800), Image.LANCZOS)
    big.save(os.path.join(DIST, 'img', pid + '.jpg'), quality=82, optimize=True, progressive=True)
    th = big.copy()
    th.thumbnail((900, 900), Image.LANCZOS)
    th.save(os.path.join(DIST, 'thumb', pid + '.jpg'), quality=78, optimize=True, progressive=True)
    r, g, b = th.resize((1, 1), Image.LANCZOS).getpixel((0, 0))
    h, s_, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    r, g, b = colorsys.hsv_to_rgb(h, min(1, s_ * 1.6), max(.55, v))
    col = '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))
    _done[path] = (pid, big.width, big.height, cam, col)
    return _done[path]


items = []
for d in photos:
    p = process(d['image'])
    if not p:
        continue
    pid, w, h, cam, col = p
    it = {'id': pid, 'title': d['title'], 'cat': d['category'], 'w': w, 'h': h,
          'exif': (d.get('camera') or cam or '').strip(), 'order': d['order'],
          'best': bool(d.get('best')), 'pick': bool(d.get('pick')), 'sw': [col]}
    vers = [v for v in (d.get('versions') or []) if v.get('image')]
    if vers:
        it['v'] = [{'id': pid, 'label': d.get('main_label') or 'Original', 'exif': it['exif']}]
        for v in vers:
            q = process(v['image'])
            if q:
                it['v'].append({'id': q[0], 'label': v.get('label') or 'Version', 'exif': it['exif'] or q[3]})
                it['sw'].append(q[4])
        if len(it['v']) == 1:
            del it['v']
    items.append(it)

bycat = {c['key']: sorted([i for i in items if i['cat'] == c['key']], key=lambda i: (i['order'], i['title']))
         for c in CATS}
CATS = [c for c in CATS if bycat[c['key']]]  # hide empty categories


def curate(key):
    allc = bycat[key]
    best = next((i for i in allc if i['best']), allc[0])
    rest = [i for i in allc if i is not best]
    picks = [i for i in rest if i['pick']][:3]
    picks += [i for i in rest if i not in picks][:3 - len(picks)]
    others = [i for i in rest if i not in picks]
    return best, picks, others


def page_file(key):
    return f'{slug(key)}.html'


# ---------------------------------------------------------------- html pieces
IG = S.get('instagram_url') or ''
IGH = S.get('instagram_handle') or ''


def datum(it):
    d = {k: it[k] for k in ('id', 'title', 'exif', 'cat', 'w', 'h')}
    if it.get('v'):
        d['v'] = it['v']
    return d


def badge(it):
    if not it.get('v'):
        return ''
    dots = ''.join(f'<b style="background:{c}"></b>' for c in it['sw'][:4])
    return f'<span class="badge"><i>{dots}</i>{len(it["v"])} filters</span>'


def fig(k, it, cls='ph', extra='', eager=False):
    ar = it['w'] / it['h']
    ex = it['exif'].split(' · ', 1)[1] if ' · ' in it['exif'] else ''
    label = f'Open {it["title"]}' + (f' (has {len(it["v"])} filter versions)' if it.get('v') else '')
    return (f'<figure class="{cls}" data-ar="{ar:.4f}" style="--ar:{ar:.4f}">'
            f'<button type="button" class="open" data-i="{k}" data-cur="View" aria-label="{E(label)}">{extra}{badge(it)}'
            f'<img src="thumb/{it["id"]}.jpg" width="{it["w"]}" height="{it["h"]}" alt="{E(it["title"])}" '
            f'loading="{"eager" if eager else "lazy"}" decoding="async">'
            f'<figcaption class="cap"><b>{E(it["title"])}</b><small>{E(ex)}</small></figcaption></button></figure>')


def bar(active, home):
    links = ''.join(f'<a href="{page_file(c["key"])}"{" class=act aria-current=page" if active == c["key"] else ""}>{E(c["name"])}</a>'
                    for c in CATS)
    ig = f'<a class="ig" href="{E(IG)}" target="_blank" rel="noopener">Instagram ↗</a>' if IG else ''
    return (f'<div class="barwrap"><div class="wrap"><div class="bar" id="bar">'
            f'<a class="mark" href="{"#top" if home else "index.html"}" aria-label="{E(S.get("alias", ""))}, home">{E(S.get("alias", ""))}</a>'
            f'<nav aria-label="Pages">{links}<a href="{"#about" if home else "index.html#about"}">About</a>{ig}</nav>'
            f'</div></div></div>')


def strip(lst):
    return ''.join(f'<button type="button" aria-label="Show {E(i["title"])}"><img src="thumb/{i["id"]}.jpg" alt="" loading="lazy"></button>'
                   for i in lst)


def display_name(name):
    """'Landscape' -> 'Land<em>scape</em>' style split for long single words; others plain."""
    return E(name)


def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace('%%' + k + '%%', v)
    return tpl


TPL = open(rp('src', 'template.html'), encoding='utf-8').read()
HERO = open(rp('src', 'hero.html'), encoding='utf-8').read()
ABOUT = open(rp('src', 'about.html'), encoding='utf-8').read()
catmap = 'const CAT=' + json.dumps({c['key']: c['name'] for c in CATS}) + ';'
TPL = re.sub(r"const CAT=\{[^}]*\};", lambda m: catmap, TPL)

common = dict(YEAR=str(datetime.date.today().year), FULLNAME=E(S.get('full_name', '')), ALIAS=E(S.get('alias', '')),
              IGURL=E(IG), IGHANDLE=E(IGH))


def head(title):
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
            f'<meta name="description" content="{E(S.get("description", ""))}">\n'
            f'<meta property="og:title" content="{E(title)}">\n'
            f'<meta property="og:description" content="{E(S.get("description", ""))}">\n'
            '<meta property="og:image" content="preview.jpg">\n<meta property="og:type" content="website">\n'
            '<meta name="twitter:card" content="summary_large_image">\n<link rel="icon" href="favicon.png">\n'
            '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
            'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n')


def document(p, title):
    i = p.index('</style>') + len('</style>')
    return head(title) + p[:i] + '\n</head>\n<body>\n' + p[i:] + '\n</body>\n</html>\n'


pages = {}

# ---- home
order = [i for c in CATS for i in bycat[c['key']]]
idx = {i['id']: k for k, i in enumerate(order)}
cards = []
for c in CATS:
    b, picks, _ = curate(c['key'])
    cards.append((b, c['name']))
first_pick = curate(CATS[0]['key'])[1][:1] if CATS else []
cards = (cards + [(p, CATS[0]['name']) for p in first_pick])[:4]
if len(cards) == 4:
    cards = [cards[2], cards[3], cards[0], cards[1]]
stack = ''.join(f'<button type="button" class="card" data-i="{idx[i["id"]]}" data-cur="View" aria-label="Open {E(i["title"])}">'
                f'<img src="thumb/{i["id"]}.jpg" alt="{E(i["title"])}"><span>{E(lab)}</span></button>' for i, lab in cards)
rib = ''
for rep in range(2):
    for k, i in enumerate(order):
        hid = ' aria-hidden="true" tabindex="-1"' if rep else ''
        rib += f'<button type="button" data-i="{k}" data-cur="View"{hid} aria-label="Open {E(i["title"])}"><img src="thumb/{i["id"]}.jpg" alt="" loading="lazy"></button>'
hero = fill(HERO, EYEBROW=E(S.get('eyebrow', '')), NAME1=E(S.get('name_line_1', '')), NAME2=E(S.get('name_line_2', '')),
            LEDE=inline(S.get('intro', '')), STACK=stack, RIBBON=rib, FULLNAME=common['FULLNAME'])

body = ''
for n, c in enumerate(CATS, 1):
    key, allc = c['key'], bycat[c['key']]
    best, picks, others = curate(key)
    head_html = (f'<header class="sech"><span class="n">{n:02d} / {len(allc):02d} photographs</span><h2>{display_name(c["name"])}</h2>'
                 f'<p>{E(c.get("subtitle", ""))}<br><a class="all" href="{page_file(key)}">See all {len(allc)} →</a></p></header>')
    if len(allc) < 5:
        tiles = ''.join(fig(idx[i['id']], i, eager=n == 1) for i in allc)
        body += f'<section class="sec" id="{key}">{head_html}<div class="grid">{tiles}</div></section>'
        continue
    tiles = fig(idx[best['id']], best, 'ph m-best', f'<span class="pick">Best of {E(c["name"])}</span>', eager=n == 1)
    tiles += ''.join(fig(idx[i['id']], i, eager=n == 1) for i in picks)
    bgs = ''.join(f'<img src="thumb/{i["id"]}.jpg" alt="" loading="lazy">' for i in (others or picks)[:3])
    cnt = f'+{len(others)}<em>more</em>' if others else 'All<em>photos</em>'
    tiles += (f'<a class="more" href="{page_file(key)}" data-cur="Open"><span class="bgs" aria-hidden="true">{bgs}</span>'
              f'<span class="in"><span class="cnt">{cnt}</span><span class="go"><span>All {len(allc)} {E(c["name"])}</span><i>→</i></span></span></a>')
    body += f'<section class="sec" id="{key}">{head_html}<div class="mosaic">{tiles}</div></section>'

facts = ''.join(f'<div><dt>{E(f.get("label", ""))}</dt><dd>{E(f.get("value", ""))}</dd></div>' for f in S.get('facts', []))
about_text = ''.join(f'<p>{inline(p.strip())}</p>' for p in re.split(r'\n\s*\n', S.get('about_text', '')) if p.strip())
about = fill(ABOUT, ABOUT_TITLE=inline(S.get('about_title', 'About')), ABOUT_TEXT=about_text, FACTS=facts,
             IGURL=E(IG), IGHANDLE=E(IGH))
if not IG:
    about = re.sub(r'<a class="igcard".*?</a>', '', about, flags=re.S)

home = fill(TPL, TITLE=E(S.get('site_title', '')), BAR=bar(None, True), TOP=hero, SECTIONS=body, NEXT='',
            ABOUT=about, STRIP=strip(order), DATA=json.dumps([datum(i) for i in order]), **common)
pages['index.html'] = document(home, S.get('site_title', ''))

# ---- category pages
for n, c in enumerate(CATS, 1):
    key, allc = c['key'], bycat[c['key']]
    best, picks, others = curate(key)
    seq = [best] + picks + others
    top = (f'<div class="wrap"><header class="phead" id="top"><div><a class="back" href="index.html">← All work</a>'
           f'<h1 class="ptitle" aria-label="{E(c["name"])}"><span class="line" data-split>{E(c["name"])}</span></h1></div>'
           f'<p class="meta page-in"><span class="n">{n:02d} / {len(allc):02d} photographs</span>{E(c.get("subtitle", ""))}</p></header></div>')
    sec = (f'<section class="sec psec page-in" id="{key}"><div class="grid">'
           + ''.join(fig(k, i, eager=k < 6) for k, i in enumerate(seq)) + '</div></section>')
    nxt = ''
    if len(CATS) > 1:
        nc = CATS[n % len(CATS)]
        th = ''.join(f'<img src="thumb/{i["id"]}.jpg" alt="" loading="lazy" style="--r:{r}deg">'
                     for i, r in zip(bycat[nc['key']][:3], (-6, 3, -2)))
        nxt = (f'<a class="next" href="{page_file(nc["key"])}" data-cur="Next"><span><small>Next</small>'
               f'<b>{E(nc["name"])} →</b></span><span class="thumbs" aria-hidden="true">{th}</span></a>')
    title = f'{c["name"]} · {S.get("full_name", "")}'
    p = fill(TPL, TITLE=E(title), BAR=bar(key, False), TOP=top, SECTIONS=sec, NEXT=nxt, ABOUT='',
             STRIP=strip(seq), DATA=json.dumps([datum(i) for i in seq]), **common)
    pages[page_file(key)] = document(p, title)

for f, p in pages.items():
    assert '%%' not in p, f'unfilled placeholder in {f}'
    open(os.path.join(DIST, f), 'w', encoding='utf-8').write(p)

# ---- share preview, icon, admin
if CATS:
    b = curate(CATS[0]['key'])[0]
    im = Image.open(os.path.join(DIST, 'img', b['id'] + '.jpg'))
    W, H = 1200, 630
    sc = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * sc) + 1, int(im.height * sc) + 1))
    t = int((im.height - H) * .3)
    im.crop((0, t, W, t + H)).save(os.path.join(DIST, 'preview.jpg'), quality=85)
fav = Image.new('RGB', (64, 64), (17, 16, 19))
ImageDraw.Draw(fav).text((32, 31), (S.get('alias') or 'R')[:1], fill=(234, 178, 160),
                          font=ImageFont.load_default(size=40), anchor='mm')
fav.save(os.path.join(DIST, 'favicon.png'))
shutil.copytree(rp('admin'), os.path.join(DIST, 'admin'))

print(f'Built {len(pages)} pages, {len(items)} photos, {len(_done)} image files -> dist/')

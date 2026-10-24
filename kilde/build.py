#!/usr/bin/env python3
"""Bygger index.html for seranodk.github.io.

1. Spil i kilde/spil.json kommer først, med deres håndskrevne tekster.
2. Derefter finder scriptet selv alle andre offentlige repos med GitHub Pages
   og lægger dem på som nye spil. Navnet tages fra <meta name="spil:navn"> eller README-overskriften,
   beskrivelsen fra første afsnit i README (ellers <meta name="description">)
   og genren fra <meta name="spil:genre">.
3. Mangler et spil et billede i kilde/billeder/, tages et ingame-skærmbillede.
Kan køres uden net; så bruges kun spil.json og de gemte data.
"""
import base64, html, json, os, re, sys, urllib.request
D = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(D)
CFG = json.load(open(os.path.join(D, 'spil.json'), encoding='utf-8'))
OWNER = CFG['bruger']
SKJUL = {x.lower() for x in CFG.get('skjul', [])} | {f'{OWNER}.github.io'.lower()}
CACHE_F = os.path.join(D, 'fundne.json')   # det sidst fundne om hvert spil
CACHE = json.load(open(CACHE_F, encoding='utf-8')) if os.path.exists(CACHE_F) else {}
RX_VER = re.compile(r"""(?:id="ver[^"]*"[^>]*>|VERSION\s*=\s*['"])[^0-9'"<]*(\d+\.\d+\.\d+)""")
# reserve: et versionsnummer som "v1.0" i <title> eller <meta name="description">
RX_VER2 = re.compile(r'<(?:title>|meta[^>]+name="description"[^>]+content=")[^<"]*?\bv(\d+\.\d+(?:\.\d+)?)')
NET = '--offline' not in sys.argv

def get(url, api=False):
    if not NET: return None
    req = urllib.request.Request(url, headers={'User-Agent': 'spilhal'})
    if api and os.environ.get('GITHUB_TOKEN'):
        req.add_header('Authorization', 'Bearer ' + os.environ['GITHUB_TOKEN'])
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return r.read().decode('utf-8', 'replace')
    except Exception as e:
        print('  kunne ikke hente', url, '-', e); return None

def page_url(repo): return os.environ.get('SPILHAL_BASE', f'https://{OWNER}.github.io/') + repo + '/'

def discover():
    """Alle offentlige repos med Pages slået til, ældste først."""
    out, n = [], 1
    while True:
        t = get(f'https://api.github.com/users/{OWNER}/repos?per_page=100&type=owner&page={n}', api=True)
        if t is None: return None
        batch = json.loads(t)
        out += batch
        if len(batch) < 100: break
        n += 1
    games = [r for r in out if r.get('has_pages') and not r.get('fork') and not r.get('archived')
             and r['name'].lower() not in SKJUL]
    return sorted(games, key=lambda r: r['created_at'])

def meta(doc, name):
    m = re.search(r'<meta[^>]+name=["\']%s["\'][^>]+content=["\']([^"\']+)' % re.escape(name), doc or '', re.I)
    return html.unescape(m.group(1)).strip() if m else None

def clean_md(t):
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', t)
    t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)
    return re.sub(r'[*_`]', '', t).strip()

def shorten(t, limit=190):
    if len(t) <= limit: return t
    cut = t[:limit]
    end = max(cut.rfind('. '), cut.rfind('! '))
    return cut[:end + 1] if end > 60 else cut.rsplit(' ', 1)[0] + '…'

def from_readme(md):
    if not md: return None, None
    title = next((clean_md(l[2:]) for l in md.splitlines() if l.startswith('# ')), None)
    para = None
    for block in re.split(r'\n\s*\n', md):
        b = block.strip()
        if b and not re.match(r'[#|\-*>`!<]|\d+\.', b):
            para = clean_md(' '.join(b.split()))
            para = re.sub(r'\s*\(?v?\d+\.\d+(\.\d+)?\)?\.?$', '', para).strip(); break
    return title, para

def auto_info(r):
    repo = r['name']
    doc = get(page_url(repo))
    md = get(f'https://raw.githubusercontent.com/{OWNER}/{repo}/{r.get("default_branch","main")}/README.md')
    rt, rp = from_readme(md)
    title = re.sub(r'\s*v?\d+\.\d+(\.\d+)?\s*$', '', meta(doc, 'spil:navn') or rt or
                   (re.search(r'<title>([^<]+)', doc or '') or [None, None])[1] or repo).strip()
    return {
        'navn': title or repo,
        'genre': meta(doc, 'spil:genre') or 'Nyt spil',
        'beskrivelse': shorten(rp or meta(doc, 'description') or r.get('description') or 'Et nyt spil fra ' + OWNER + '.'),
    }

def version(repo, doc=None):
    doc = doc if doc is not None else get(page_url(repo))
    m = RX_VER.search(doc or '') or RX_VER2.search(doc or '')
    return m.group(1) if m else CACHE.get(repo, {}).get('version', '')

def image(repo):
    f = os.path.join(D, 'billeder', repo.lower() + '.webp')
    if not os.path.exists(f) and NET:
        print('  tager skærmbillede af', repo)
        try:
            from screenshot import take
            take(page_url(repo), f)
            if os.path.getsize(f) < 3000:   # tomt billede: spillet var ikke klar, prøv igen næste gang
                os.remove(f); print('  billedet var tomt, prøver igen senere')
        except Exception as e:
            print('  skærmbillede fejlede:', e)
    if not os.path.exists(f): return ''
    return 'data:image/webp;base64,' + base64.b64encode(open(f, 'rb').read()).decode()

sys.path.insert(0, D)
games = []
curated = {g['repo'].lower(): g for g in CFG['spil']}
for g in CFG['spil']:
    if g['repo'].lower() in SKJUL: continue
    games.append(dict(g))
found = discover()
if found is None:
    print('Ingen forbindelse til GitHub, bruger gemte spil')
    for repo, info in CACHE.items():
        if repo.lower() not in curated and repo.lower() not in SKJUL:
            games.append(dict(info, repo=repo))
else:
    # brug repoets rigtige stavemåde (Pages skelner mellem store og små bogstaver)
    real = {r['name'].lower(): r['name'] for r in found}
    for g in games:
        g['repo'] = real.get(g['repo'].lower(), g['repo'])
    for r in found:
        if r['name'].lower() in curated: continue
        if get(f'https://raw.githubusercontent.com/{OWNER}/{r["name"]}/{r.get("default_branch","main")}/index.html') is None:
            print('Springer over (ingen index.html endnu):', r['name']); CACHE.pop(r['name'], None); continue
        print('Fundet nyt spil:', r['name'])
        games.append(dict(auto_info(r), repo=r['name']))
for g in games:
    g['version'] = version(g['repo'])
    g['url'] = page_url(g['repo'])
    g['img'] = image(g['repo'])
    if g['repo'].lower() not in curated:
        CACHE[g['repo']] = {k: g[k] for k in ('navn', 'genre', 'beskrivelse', 'version')}
    else:
        CACHE.setdefault(g['repo'], {})['version'] = g['version']
json.dump(CACHE, open(CACHE_F, 'w', encoding='utf-8'), ensure_ascii=False, indent=2, sort_keys=True)

def card(g):
    e = html.escape
    ver = f'<span class="ver" title="Nyeste version">v{e(g["version"])}</span>' if g['version'] else '<span class="ver" title="Nyeste version" hidden></span>'
    img = f'<img src="{g["img"]}" alt="Skærmbillede fra {e(g["navn"])}" width="480" height="480">' if g['img'] else ''
    return f"""
<a class="card" href="{g['url']}" data-game="{g['url']}" data-repo="{e(g['repo'])}" aria-label="Spil {e(g['navn'])}">
  <span class="shot">{img}</span>
  <span class="body">
    <span class="meta"><span class="genre">{e(g['genre'])}</span>{ver}</span>
    <span class="name">{e(g['navn'])}</span>
    <span class="desc">{e(g['beskrivelse'])}</span>
    <span class="play">Spil <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3l7 5-7 5z"/></svg></span>
  </span>
</a>"""
cards = ''.join(card(g) for g in games)
COUNT = {1:'Ét lille spil',2:'To små spil',3:'Tre små spil',4:'Fire små spil',5:'Fem små spil',6:'Seks små spil',
         7:'Syv små spil',8:'Otte små spil',9:'Ni små spil',10:'Ti små spil'}.get(len(games), f'{len(games)} små spil')

head='''<title>Troels' Spilhal</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="theme-color" content="#0b0d14">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Silkscreen&family=Figtree:wght@400;500;700&display=swap">
<style>
/* Layout: one column of wide cabinet cards, screenshot left, text right; 2 columns on desktop */
:root{
  --bg:#0b0d14; --panel:#141824; --line:#252b3d; --fg:#eef1f8; --muted:#9aa3ba; --accent:#ffd23f;
  --display:"Silkscreen","Courier New",monospace; --body:"Figtree",system-ui,-apple-system,"Segoe UI",sans-serif;
  color-scheme:dark;
}
html{background:var(--bg)}
body{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:16px;line-height:1.5;margin:0;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));
  -webkit-text-size-adjust:100%}
.wrap{max-width:980px;margin:0 auto;padding-block:40px 48px;display:flex;flex-direction:column;gap:28px}
header{display:flex;flex-direction:column;gap:8px}
h1{font-family:var(--display);font-weight:400;font-size:clamp(28px,6vw,44px);line-height:1.1;margin:0;letter-spacing:.02em;text-wrap:balance}
h1 .coin{color:var(--accent)}
.lede{color:var(--muted);margin:0;max-width:52ch}
.grid{display:grid;grid-template-columns:1fr;gap:14px}
@media (min-width:760px){.grid{grid-template-columns:1fr 1fr}}
.card{display:grid;grid-template-columns:112px 1fr;gap:14px;align-items:start;padding:12px;border:1px solid var(--line);
  border-radius:14px;background:var(--panel);color:inherit;text-decoration:none;
  transition:transform .15s ease,border-color .15s ease;-webkit-tap-highlight-color:transparent}
@media (min-width:420px){.card{grid-template-columns:132px 1fr}}
.card:hover{border-color:var(--accent);transform:translateY(-2px)}
.card:active{transform:scale(.985)}
.card:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.shot{display:block;aspect-ratio:1;max-width:100%;border-radius:22%;overflow:hidden;background:#000;
  box-shadow:0 0 0 1px rgba(255,255,255,.08) inset}
.shot img{display:block;width:100%;height:100%;object-fit:cover}
.letter{display:grid;place-items:center;width:100%;height:100%;font-family:var(--display);font-size:44px;color:var(--bg);background:var(--accent)}
.card.new .genre{color:var(--accent)}
.body{display:flex;flex-direction:column;gap:4px;min-width:0}
.meta{display:flex;gap:8px;align-items:center;font-size:12px;color:var(--muted)}
.genre{text-transform:uppercase;letter-spacing:.08em;font-weight:700}
.ver{font-variant-numeric:tabular-nums;border:1px solid var(--line);border-radius:99px;padding:0 7px}
.name{font-family:var(--display);font-size:19px;line-height:1.2}
.desc{color:var(--muted);font-size:14px;line-height:1.45}
.play{margin-top:4px;display:inline-flex;align-items:center;gap:6px;font-weight:700;font-size:14px;color:var(--accent)}
.play svg{width:12px;height:12px;fill:currentColor}
footer{color:var(--muted);font-size:13px;border-top:1px solid var(--line);padding-top:16px}
footer a{color:var(--fg)}
@media (prefers-reduced-motion:reduce){.card{transition:none}.card:hover{transform:none}}
</style>'''
SCRIPT=r'''<script>
/* 1) Henter versionsnummeret fra hvert spils index.html, så kortet viser den version, der ligger ude nu.
   2) Spørger GitHub, hver gang siden åbnes, om der er kommet et nyt repo med Pages.
      Et nyt spil vises med det samme; det rigtige skærmbillede kommer, når den automatiske opdatering har kørt. */
(function(){
  var OWNER='__OWNER__', BASE='https://'+OWNER+'.github.io/', SKJUL=__SKJUL__;
  var RX=/(?:id="ver[^"]*"[^>]*>|VERSION\s*=\s*['"])[^0-9'"<]*(\d+\.\d+\.\d+)/;
  var RX2=/<(?:title>|meta[^>]+name="description"[^>]+content=")[^<"]*?\bv(\d+\.\d+(?:\.\d+)?)/;
  var grid=document.querySelector('.grid');
  function version(card){
    var badge=card.querySelector('.ver');
    fetch(card.dataset.game+'?t='+Date.now(),{cache:'no-store'})
      .then(function(r){return r.ok?r.text():Promise.reject(r.status)})
      .then(function(html){var m=html.match(RX)||html.match(RX2); if(m){badge.textContent='v'+m[1];badge.hidden=false;}})
      .catch(function(){});
  }
  function count(){
    var n=grid.querySelectorAll('.card').length, el=document.getElementById('count');
    var w=['','Ét lille spil','To små spil','Tre små spil','Fire små spil','Fem små spil','Seks små spil','Syv små spil','Otte små spil','Ni små spil','Ti små spil'];
    if(el) el.textContent=w[n]||(n+' små spil');
  }
  function clean(t){return t.replace(/!\[[^\]]*\]\([^)]*\)/g,'').replace(/\[([^\]]+)\]\([^)]*\)/g,'$1').replace(/[*_`]/g,'').trim();}
  function shorten(t){if(t.length<=190)return t;var c=t.slice(0,190),e=Math.max(c.lastIndexOf('. '),c.lastIndexOf('! '));return e>60?c.slice(0,e+1):c.replace(/\s+\S*$/,'')+'…';}
  function readme(r,card){
    fetch('https://raw.githubusercontent.com/'+OWNER+'/'+r.name+'/'+(r.default_branch||'main')+'/README.md')
      .then(function(x){return x.ok?x.text():Promise.reject()})
      .then(function(md){
        var h=md.split('\n').filter(function(l){return l.indexOf('# ')===0})[0];
        if(h) card.querySelector('.name').textContent=clean(h.slice(2));
        var blocks=md.split(/\n\s*\n/);
        for(var i=0;i<blocks.length;i++){var b=blocks[i].trim();
          if(b&&!/^([#|\-*>`!<]|\d+\.)/.test(b)){
            card.querySelector('.desc').textContent=shorten(clean(b.split(/\s+/).join(' ')).replace(/\s*\(?v?\d+\.\d+(\.\d+)?\)?\.?$/,''));break;}}
      }).catch(function(){});
  }
  function add(r){
    var url=BASE+r.name+'/', a=document.createElement('a');
    a.className='card new'; a.href=url; a.dataset.game=url; a.dataset.repo=r.name; a.setAttribute('aria-label','Spil '+r.name);
    a.innerHTML='<span class="shot"><span class="letter"></span></span><span class="body"><span class="meta"><span class="genre">Nyt spil</span><span class="ver" title="Nyeste version" hidden></span></span><span class="name"></span><span class="desc"></span><span class="play">Spil <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3l7 5-7 5z"/></svg></span></span>';
    a.querySelector('.letter').textContent=r.name.charAt(0).toUpperCase();
    a.querySelector('.name').textContent=r.name;
    a.querySelector('.desc').textContent=r.description||'Et nyt spil. Billede og beskrivelse kommer om lidt.';
    var img=new Image(); img.alt='Ikon for '+r.name; img.width=480; img.height=480;
    img.onload=function(){var s=a.querySelector('.shot');s.innerHTML='';s.appendChild(img);};
    img.src=url+'icon-512.png';
    grid.appendChild(a); version(a); readme(r,a); count();
  }
  document.querySelectorAll('.card[data-game]').forEach(version);
  var known={}; SKJUL.concat([OWNER+'.github.io']).forEach(function(n){known[n.toLowerCase()]=1});
  document.querySelectorAll('.card[data-repo]').forEach(function(c){known[c.dataset.repo.toLowerCase()]=1});
  fetch('https://api.github.com/users/'+OWNER+'/repos?per_page=100&type=owner&t='+Date.now())
    .then(function(r){return r.ok?r.json():Promise.reject(r.status)})
    .then(function(list){
      list.filter(function(r){return r.has_pages&&!r.fork&&!r.archived&&!known[r.name.toLowerCase()]})
          .sort(function(x,y){return x.created_at<y.created_at?-1:1}).forEach(function(r){
            /* kun repos, der faktisk har et spil (index.html) */
            fetch('https://raw.githubusercontent.com/'+OWNER+'/'+r.name+'/'+(r.default_branch||'main')+'/index.html',{method:'HEAD'})
              .then(function(x){if(x.ok)add(r);}).catch(function(){});
          });
    }).catch(function(){});
})();
</script>'''
main=f'''<main class="wrap">
<header>
  <h1>Troels' Spilhal<span class="coin">.</span></h1>
  <p class="lede"><span id="count">{COUNT}</span>, der kører i browseren på både mobil og computer. Tryk på et spil for at starte.</p>
</header>
<nav class="grid" aria-label="Spil">{cards}
</nav>
<footer>Tip: Åbn et spil på mobilen og vælg <b>Føj til hjemmeskærm</b>, så starter det i fuld skærm som en app. Kildekoden ligger på <a href="https://github.com/seranodk">github.com/seranodk</a>.</footer>
</main>
{SCRIPT.replace('__OWNER__', OWNER).replace('__SKJUL__', json.dumps(sorted(SKJUL)))}'''
open(os.path.join(ROOT,'index.html'),'w',encoding='utf-8').write('<!doctype html>\n<html lang="da">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'+head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n','')+'\n</head>\n<body>\n'+main+'\n</body>\n</html>\n')
if '--artifact' in sys.argv:
    open(os.path.join(D,'artifact.html'),'w',encoding='utf-8').write(head+'\n'+main)
print('Bygget index.html med', len(games), 'spil')

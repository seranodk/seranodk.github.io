import base64, os
D=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(D)
def b64(n): return 'data:image/webp;base64,'+base64.b64encode(open(os.path.join(D,'billeder',n+'.webp'),'rb').read()).decode()
games=[
 ('sensible','Sensible','0.35.1','Fodbold','https://seranodk.github.io/sensible/',
  'Top-down fodbold i Sensible Soccer-stil med rigtige hold fra Premier League, La Liga, Bundesliga og Superligaen. Hurtig kamp, venskabskamp eller to spillere.'),
 ('ishockey','Ishockey','0.7.0','Ishockey','https://seranodk.github.io/Ishockey/',
  'Retro ishockey ovenfra på en lodret bane. Skøjt, aflevér og skyd med tommelfingeren, og slå icing og offside til eller fra.'),
 ('brikker','Brikker','0.2.0','Murbryder','https://seranodk.github.io/Brikker/',
  'Murbryder med fysik som i Arkanoid. Otte runder, sølv- og guldbrikker og syv kapsler. Vælg mellem temaerne Neon, Klassisk og Papir.'),
 ('labyrint','Labyrint','0.2.0','Labyrint','https://seranodk.github.io/Labyrint/',
  'Spis alle prikker og hold dig fra de fire jægere. Nye baner i fem størrelser og fem temaer, og et joystick der aldrig kører fast.'),
]
cards=''.join(f'''
<a class="card" href="{u}" data-game="{u}" aria-label="Spil {n}">
  <span class="shot"><img src="{b64(k)}" alt="Skærmbillede fra {n}" width="480" height="480"></span>
  <span class="body">
    <span class="meta"><span class="genre">{g}</span><span class="ver" title="Nyeste version">v{v}</span></span>
    <span class="name">{n}</span>
    <span class="desc">{d}</span>
    <span class="play">Spil <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3l7 5-7 5z"/></svg></span>
  </span>
</a>''' for k,n,v,g,u,d in games)

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
/* Henter versionsnummeret direkte fra hvert spils index.html på GitHub Pages,
   så kortene altid viser den version, der ligger ude lige nu. */
(function(){
  var RX=/(?:id="ver[^"]*"[^>]*>|VERSION\s*=\s*['"])[^0-9'"<]*(\d+\.\d+\.\d+)/;
  document.querySelectorAll('.card[data-game]').forEach(function(card){
    var badge=card.querySelector('.ver');
    fetch(card.dataset.game+'?t='+Date.now(),{cache:'no-store'})
      .then(function(r){return r.ok?r.text():Promise.reject(r.status)})
      .then(function(html){var m=html.match(RX); if(m) badge.textContent='v'+m[1];})
      .catch(function(){});
  });
})();
</script>'''
main=f'''<main class="wrap">
<header>
  <h1>Troels' Spilhal<span class="coin">.</span></h1>
  <p class="lede">Fire små spil, der kører i browseren på både mobil og computer. Tryk på et spil for at starte.</p>
</header>
<nav class="grid" aria-label="Spil">{cards}
</nav>
<footer>Tip: Åbn et spil på mobilen og vælg <b>Føj til hjemmeskærm</b>, så starter det i fuld skærm som en app. Kildekoden ligger på <a href="https://github.com/seranodk">github.com/seranodk</a>.</footer>
</main>
{SCRIPT}'''
open(os.path.join(D,'artifact.html'),'w').write(head+'\n'+main)
open(os.path.join(ROOT,'index.html'),'w').write('<!doctype html>\n<html lang="da">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'+head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n','')+'\n</head>\n<body>\n'+main+'\n</body>\n</html>\n')

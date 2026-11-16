"""Laver offline.json: listen over alle filer, Spillehallen skal gemme på telefonen,
så alle spil kan spilles uden net (fx i et fly).

For hvert spil hentes repoets filliste fra GitHub. Med kommer selve siden og de filer,
spillet bruger (billeder, ikoner, lyde, scripts, data), men ikke udviklerfiler som
README, byggescripts, test, gamle versioner og demo-videoer. Desuden kommer de
Google-skrifttyper med, som spillene henter udefra.
"""
import hashlib
import json
import os
import re

MED = re.compile(r'\.(html|js|css|png|jpe?g|webp|gif|svg|ico|webmanifest|json|mp3|ogg|wav|m4a|aac|woff2?|ttf|otf)$', re.I)
UDEN_MAPPER = re.compile(r'^(versioner|versions|arkiv|artifact|src|test|tests|demo|tools|kilde|scripts|\.github)/', re.I)
UDEN_FILER = re.compile(r'(^|/)(game\.html|sw\.js|firebase[^/]*\.json|package(-lock)?\.json|[^/]*-v\d+[\d.]*\.html)$', re.I)
SKRIFT = re.compile(r'https://fonts\.googleapis\.com/css2?\?[^"\'\s<>]+')


def _tree(get, owner, repo, branch):
    t = get(f'https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1', api=True)
    if t is None:
        return None
    d = json.loads(t)
    return d.get('sha', ''), [(x['path'], x.get('size', 0)) for x in d.get('tree', []) if x.get('type') == 'blob']


def byg(games, get, cache, owner, root, page_url, egne_filer, skrifter_her):
    """Skriver offline.json i root og returnerer antal spil med filer."""
    spil, skrifter, nogle = [], set(skrifter_her), []
    for g in games:
        repo = g['repo']
        info = cache.setdefault(repo, {})
        res = _tree(get, owner, repo, g.get('branch', 'main'))
        if res:
            sha, filer = res
            valgt = [(p, s) for p, s in filer if MED.search(p) and not UDEN_MAPPER.search(p) and not UDEN_FILER.search(p)]
            info['offline'] = {'sha': sha, 'filer': valgt}
        off = info.get('offline')
        if not off:
            continue
        base = page_url(repo)
        urls = [base] + [base + p for p, _ in off['filer']]
        doc = g.get('_doc') or ''
        skrifter.update(m.group(0).replace('&amp;', '&') for m in SKRIFT.finditer(doc))
        spil.append({'repo': repo, 'navn': g['navn'], 'filer': urls, 'bytes': sum(s for _, s in off['filer'])})
        nogle.append(off['sha'])
    data = {
        'egne': egne_filer,
        'skrifter': sorted(skrifter),
        'spil': spil,
    }
    data['id'] = hashlib.sha1(json.dumps([nogle, data['egne'], data['skrifter'], [s['repo'] for s in spil]]).encode()).hexdigest()[:12]
    with open(os.path.join(root, 'offline.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return len(spil)

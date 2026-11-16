/* Spil uden net: gemmer Spillehallen og alle spil på enheden og holder dem opdateret. */
(function(){
  if(!('serviceWorker' in navigator) || !('caches' in window) || !/github\.io$/.test(location.hostname)) return;
  navigator.serviceWorker.register('/sw.js').catch(function(){});
  var CACHE='spillehal-offline', $=function(i){return document.getElementById(i)};
  var boks=$('offline'), knap=$('offKnap'), titel=$('offTitel'), status=$('offStatus'), bar=$('offBar'), fyld=$('offFyld'), tip=$('offTip');
  boks.hidden=false;
  function hent(k){try{return localStorage.getItem(k)}catch(e){return null}}
  function gem(k,v){try{localStorage.setItem(k,v)}catch(e){}}
  var ios=/iP(hone|ad|od)/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  var app=navigator.standalone||matchMedia('(display-mode: standalone)').matches;
  var mb=function(b){return (b/1048576).toFixed(b<1048576*10?1:0).replace('.',',')+' MB'};
  var igang=false;

  function visGemt(antal, naar){
    boks.classList.add('ok'); bar.hidden=true;
    titel.textContent=antal+' spil gemt til brug uden net';
    status.textContent=(navigator.onLine?'Opdateres automatisk, når du har net.':'Du er offline. Alle gemte spil kan spilles.')+(naar?' Senest: '+naar+'.':'');
    knap.textContent='Opdater nu'; knap.disabled=!navigator.onLine;
    tip.hidden=!(ios&&!app);
  }
  async function liste(){
    var r=await fetch('/offline.json?t='+Date.now(),{cache:'no-store'}); if(!r.ok) throw new Error('liste');
    return r.json();
  }
  async function gemFil(c,url){
    var u=new URL(url,location.href), egen=u.origin===location.origin;
    var r=await fetch(url,{cache:'reload',mode:egen?'same-origin':'cors',credentials:'omit'});
    if(!r.ok) throw new Error(r.status);
    await c.put(url,r.clone());
    if(/fonts\.googleapis\.com/.test(url)){            /* skrifttypernes egne filer */
      var css=await r.text(), m, rx=/url\((https:\/\/fonts\.gstatic\.com\/[^)]+)\)/g, out=[];
      while((m=rx.exec(css))) out.push(m[1]);
      await Promise.all(out.map(function(f){return fetch(f,{mode:'cors'}).then(function(x){if(x.ok) return c.put(f,x)}).catch(function(){})}));
    }
  }
  async function hentAlt(stille){
    if(igang||!navigator.onLine) return; igang=true;
    try{
      var l=await liste(), c=await caches.open(CACHE);
      if(navigator.storage&&navigator.storage.persist) navigator.storage.persist().catch(function(){});
      var opgaver=[]; l.egne.concat(l.skrifter).forEach(function(u){opgaver.push({u:u})});
      l.spil.forEach(function(s,i){s.filer.forEach(function(u){opgaver.push({u:u,s:i})})});
      var total=l.spil.reduce(function(a,s){return a+s.bytes},0), klar=0, fejl=0, spilFejl={};
      if(!stille){knap.disabled=true; bar.hidden=false; titel.textContent='Henter spillene ('+mb(total)+')…'; boks.classList.remove('ok');}
      var i=0;
      async function arbejder(){
        while(i<opgaver.length){var o=opgaver[i++];
          try{await gemFil(c,o.u)}catch(e){fejl++; if(o.s!=null) spilFejl[o.s]=1}
          klar++; if(!stille){fyld.style.width=Math.round(klar/opgaver.length*100)+'%'; status.textContent=klar+' af '+opgaver.length+' filer';}
        }
      }
      await Promise.all([arbejder(),arbejder(),arbejder(),arbejder()]);
      var ok=l.spil.length-Object.keys(spilFejl).length, naar=new Date().toLocaleString('da-DK',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
      gem('spillehal-offline',l.id); gem('spillehal-offline-naar',naar); gem('spillehal-offline-antal',String(ok));
      visGemt(ok,naar);
      if(fejl&&!stille) status.textContent+=' '+(fejl===1?'1 fil':fejl+' filer')+' kunne ikke hentes; prøv "Opdater nu" igen.';
    }catch(e){
      if(!stille){titel.textContent='Spil uden net'; status.textContent='Spillene kunne ikke hentes lige nu. Tjek din forbindelse og prøv igen.'; bar.hidden=true;}
    }
    knap.disabled=!navigator.onLine; igang=false;
  }
  knap.addEventListener('click',function(){hentAlt(false)});
  addEventListener('online',function(){ if(hent('spillehal-offline')) visGemt(hent('spillehal-offline-antal'),hent('spillehal-offline-naar')); });
  addEventListener('offline',function(){ if(hent('spillehal-offline')) visGemt(hent('spillehal-offline-antal'),hent('spillehal-offline-naar')); else {status.textContent='Du er offline.'; knap.disabled=true;} });
  if(hent('spillehal-offline')){
    visGemt(hent('spillehal-offline-antal'),hent('spillehal-offline-naar'));
    /* har man hentet før: opdater stille, når der er nye spil eller nye versioner */
    if(navigator.onLine) liste().then(function(l){ if(l.id!==hent('spillehal-offline')) hentAlt(true); }).catch(function(){});
  } else if(!navigator.onLine){ status.textContent='Du er offline. Hent spillene, næste gang du har net.'; knap.disabled=true; }
})();

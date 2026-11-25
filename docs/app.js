const demo=[['Morning Crossing','Buck','North Ridge','2026-10-18 06:42'],['The Evening Visitor','Doe','Creek Bottom','2026-10-17 18:24'],['Between the Pines','Buck','Oak Flat','2026-10-16 07:08'],['At First Light','Buck','North Ridge','2026-10-15 06:11'],['Quiet on the Trail','Other','Creek Bottom','2026-10-13 19:50'],['The Old Trail','Doe','Oak Flat','2026-10-11 08:35']].map((x,i)=>({id:'demo'+i,title:x[0],type:x[1],camera:x[2],captured_at:x[3],url:'assets/forest.svg',demo:true}));
const $=s=>document.querySelector(s);
let images=[],subset=[],filter='all',cam='all',cur=0;
$('#year').textContent=new Date().getFullYear();

function safe(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
// "2026-10-18 06:42" -> "Oct 18, 2026 · 6:42 AM"
function pretty(s){const m=String(s||'').match(/^(\d{4})-(\d\d)-(\d\d)[ T](\d\d):(\d\d)/);if(!m)return String(s||'');const d=new Date(+m[1],m[2]-1,+m[3],+m[4],+m[5]);return d.toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'})+' · '+d.toLocaleTimeString(undefined,{hour:'numeric',minute:'2-digit'})}
const isNew=p=>!p.demo&&images[0]&&p.captured_at&&p.captured_at.slice(0,10)===images[0].captured_at.slice(0,10);

function show(){
  subset=images.filter(p=>(filter==='all'||p.type===filter)&&(cam==='all'||p.camera===cam));
  $('#photoGrid').innerHTML=subset.map(p=>`<article class="tile" tabindex="0" role="button" data-id="${safe(p.id)}"><img loading="lazy" src="${safe(p.thumb||p.url)}" alt="${safe(p.title)}"><div class="tile-info"><span class="tile-tag">${safe(p.type).toUpperCase()}${p.demo?' · DEMO':''}${isNew(p)?'<span class="new">NEW</span>':''}</span><h3>${safe(p.title)}</h3><div class="tile-meta"><span>⌾ ${safe(p.camera)}</span><span>${safe(pretty(p.captured_at))}</span></div></div></article>`).join('');
  $('#empty').hidden=subset.length!==0;
}

function open(id){
  let list=subset.some(p=>p.id===id)?subset:images;
  cur=list.findIndex(p=>p.id===id);if(cur<0)return;
  openList=list;paint();$('#lightbox').showModal();
}
let openList=[];
function paint(){const p=openList[cur];$('#large').src=p.url;$('#large').alt=p.title;$('#detail').textContent=`${p.title} · ${p.camera} · ${pretty(p.captured_at)}`;}
function step(n){if(!openList.length)return;cur=(cur+n+openList.length)%openList.length;paint();}

function hero(){
  const p=images[0];if(!p||p.demo)return;
  const pic=$('#heroPic');
  pic.style.backgroundImage=`linear-gradient(90deg,#19291e2e,transparent),url("${encodeURI(p.url)}")`;
  pic.classList.add('live');pic.tabIndex=0;pic.setAttribute('role','button');
  pic.setAttribute('aria-label',`Latest photo: ${p.title}, ${p.camera}. Open full size.`);
  $('#heroKicker').textContent='LATEST SIGHTING';
  $('#heroTitle').textContent=p.camera.toUpperCase();
  $('#heroMeta').textContent=pretty(p.captured_at);
  pic.addEventListener('click',()=>open(p.id));
  pic.addEventListener('keydown',e=>{if(e.key==='Enter')open(p.id)});
}

function init(data){
  images=(data.length?data:demo).slice().sort((a,b)=>String(b.captured_at).localeCompare(String(a.captured_at)));
  $('#count').textContent=String(images.length).padStart(2,'0');
  const cams=[...new Set(images.map(i=>i.camera))].sort();
  $('#camCount').textContent=String(cams.length).padStart(2,'0');
  $('#newest').textContent=data.length?(pretty(images[0].captured_at).split(',')[0]||'NEW'):'DEMO';
  $('#camFilters').innerHTML='<span class="filter-label">CAMERA</span><button class="active" data-cam="all">All cameras</button>'+cams.map(c=>`<button data-cam="${safe(c)}">${safe(c)}</button>`).join('');
  if(data.length)$('#hint').hidden=true;
  hero();show();
}

$('#typeFilters').addEventListener('click',e=>{const b=e.target.closest('button[data-filter]');if(!b)return;filter=b.dataset.filter;document.querySelectorAll('#typeFilters button').forEach(x=>x.classList.toggle('active',x===b));show()});
$('#camFilters').addEventListener('click',e=>{const b=e.target.closest('button[data-cam]');if(!b)return;cam=b.dataset.cam;document.querySelectorAll('#camFilters button').forEach(x=>x.classList.toggle('active',x===b));show()});
$('#photoGrid').addEventListener('click',e=>{const t=e.target.closest('.tile');if(t)open(t.dataset.id)});
$('#photoGrid').addEventListener('keydown',e=>{const t=e.target.closest('.tile');if(t&&e.key==='Enter')open(t.dataset.id)});
$('#prev').addEventListener('click',()=>step(-1));
$('#next').addEventListener('click',()=>step(1));
document.addEventListener('keydown',e=>{if(!$('#lightbox').open)return;if(e.key==='ArrowRight')step(1);if(e.key==='ArrowLeft')step(-1)});
let tx=null;$('#lightbox').addEventListener('touchstart',e=>tx=e.touches[0].clientX,{passive:true});
$('#lightbox').addEventListener('touchend',e=>{if(tx===null)return;const dx=e.changedTouches[0].clientX-tx;if(Math.abs(dx)>50)step(dx<0?1:-1);tx=null});
$('#close').addEventListener('click',()=>$('#lightbox').close());
$('#lightbox').addEventListener('click',e=>{if(e.target.id==='lightbox')$('#lightbox').close()});
fetch('gallery.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>init(Array.isArray(d.photos)?d.photos:[])).catch(()=>init([]));

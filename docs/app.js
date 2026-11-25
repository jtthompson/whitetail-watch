const demo=[['Morning Crossing','Buck','North Ridge','2026-10-18 06:42'],['The Evening Visitor','Doe','Creek Bottom','2026-10-17 18:24'],['Between the Pines','Buck','Oak Flat','2026-10-16 07:08'],['At First Light','Buck','North Ridge','2026-10-15 06:11'],['Quiet on the Trail','Other','Creek Bottom','2026-10-13 19:50'],['The Old Trail','Doe','Oak Flat','2026-10-11 08:35']].map((x,i)=>({id:'demo'+i,title:x[0],type:x[1],camera:x[2],captured_at:x[3],url:'assets/forest.svg',demo:true}));
const $=s=>document.querySelector(s);
let images=[],subset=[],filter='all',cam='all',cur=0,openList=[];
$('#year').textContent=new Date().getFullYear();

// ---- Owner edits (favorites / removals) ---------------------------------
// Saved in docs/edits.json through the GitHub API with the owner's own access key.
// The repository is worked out from the site address: OWNER.github.io/REPO/
const REPO=(()=>{const o=location.hostname.split('.')[0];const r=location.pathname.split('/').filter(Boolean)[0];
  return location.hostname.endsWith('github.io')&&r?`${o}/${r}`:'jtthompson/whitetail-watch'})();
const API=`https://api.github.com/repos/${REPO}`;
const EDITS_PATH='docs/edits.json';
let edits={favorites:[],removed:[]};      // what the public site shows
let pending=new Map();                     // id -> {fav?:bool, removed?:bool} not yet saved
let token=null;
try{token=localStorage.getItem('ww-owner-token')}catch(e){}
const isOwner=()=>!!token;

function safe(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
// "2026-10-18 06:42" -> "Oct 18, 2026 · 6:42 AM"
function pretty(s){const m=String(s||'').match(/^(\d{4})-(\d\d)-(\d\d)[ T](\d\d):(\d\d)/);if(!m)return String(s||'');const d=new Date(+m[1],m[2]-1,+m[3],+m[4],+m[5]);return d.toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'})+' · '+d.toLocaleTimeString(undefined,{hour:'numeric',minute:'2-digit'})}

function isFav(id){const p=pending.get(id);return p&&'fav' in p?p.fav:edits.favorites.includes(id)}
function isRemoved(id){const p=pending.get(id);return p&&'removed' in p?p.removed:edits.removed.includes(id)}
function setPending(id,key,val){
  const saved=key==='fav'?edits.favorites.includes(id):edits.removed.includes(id);
  const p={...(pending.get(id)||{})};
  if(val===saved)delete p[key];else p[key]=val;
  if(Object.keys(p).length)pending.set(id,p);else pending.delete(id);
  refresh();
}
const visible=()=>images.filter(p=>isOwner()||!isRemoved(p.id));
const isNew=p=>!p.demo&&images[0]&&p.captured_at&&p.captured_at.slice(0,10)===images[0].captured_at.slice(0,10);

function tile(p){
  const fav=isFav(p.id),gone=isRemoved(p.id);
  const admin=isOwner()&&!p.demo?`<div class="adm"><button type="button" class="adm-fav${fav?' on':''}" data-act="fav" aria-pressed="${fav}" aria-label="${fav?'Remove from favorites':'Add to favorites'}">${fav?'★':'☆'}</button><button type="button" class="adm-del" data-act="del" aria-label="${gone?'Keep this photo':'Remove this photo'}">${gone?'Undo':'Remove'}</button></div>`:'';
  return `<article class="tile${gone?' gone':''}" tabindex="0" role="button" data-id="${safe(p.id)}">${admin}<img loading="lazy" src="${safe(p.thumb||p.url)}" alt="${safe(p.title)}"><div class="tile-info"><span class="tile-tag">${safe(p.type).toUpperCase()}${p.demo?' · DEMO':''}${isNew(p)?'<span class="new">NEW</span>':''}${fav?'<span class="star" aria-label="Favorite">★</span>':''}</span><h3>${safe(p.title)}</h3><div class="tile-meta"><span>⌾ ${safe(p.camera)}</span><span>${safe(pretty(p.captured_at))}</span></div>${gone?'<p class="gone-note">Will be removed when you save</p>':''}</div></article>`;
}

function show(){
  subset=visible().filter(p=>(filter==='all'||p.type===filter)&&(cam==='all'||p.camera===cam));
  $('#photoGrid').innerHTML=subset.map(tile).join('');
  $('#empty').hidden=subset.length!==0;
  const favs=visible().filter(p=>isFav(p.id));
  $('#favorites').hidden=!favs.length&&!isOwner();
  $('#favNav').hidden=!favs.length;
  $('#favStrip').innerHTML=favs.length?favs.map(tile).join(''):'<p class="fav-empty">No favorites yet. Tap ☆ on any photo to add it here.</p>';
}

function stats(){
  const live=images.filter(p=>!edits.removed.includes(p.id));
  $('#count').textContent=String(live.length).padStart(2,'0');
  const cams=[...new Set(live.map(i=>i.camera))].sort();
  $('#camCount').textContent=String(cams.length).padStart(2,'0');
  $('#newest').textContent=live.length&&!live[0].demo?(pretty(live[0].captured_at).split(',')[0]||'NEW'):'DEMO';
  $('#camFilters').innerHTML='<span class="filter-label">CAMERA</span>'+['all',...cams].map(c=>`<button class="${c===cam?'active':''}" data-cam="${safe(c)}">${c==='all'?'All cameras':safe(c)}</button>`).join('');
}

function refresh(){show();adminBar();if($('#lightbox').open)paint()}

function open(id){
  const list=subset.some(p=>p.id===id)?subset:visible();
  cur=list.findIndex(p=>p.id===id);if(cur<0)return;
  openList=list;paint();$('#lightbox').showModal();
}
function paint(){const p=openList[cur];if(!p)return;$('#large').src=p.url;$('#large').alt=p.title;$('#detail').textContent=`${p.title} · ${p.camera} · ${pretty(p.captured_at)}`;
  const own=isOwner()&&!p.demo;$('#lbAdmin').hidden=!own;
  if(own){const f=isFav(p.id),g=isRemoved(p.id);$('#lbFav').textContent=f?'★ Favorite':'☆ Favorite';$('#lbFav').classList.toggle('on',f);$('#lbRemove').textContent=g?'Keep photo':'Remove photo';$('#lbRemove').classList.toggle('on',g)}}
function step(n){if(!openList.length)return;cur=(cur+n+openList.length)%openList.length;paint();}

let heroBound=false;
function hero(){
  const p=images.find(x=>!edits.removed.includes(x.id));
  const pic=$('#heroPic');if(!p||p.demo)return;
  pic.style.backgroundImage=`linear-gradient(90deg,#19291e2e,transparent),url("${encodeURI(p.url)}")`;
  pic.classList.add('live');pic.tabIndex=0;pic.setAttribute('role','button');pic.dataset.id=p.id;
  pic.setAttribute('aria-label',`Latest photo: ${p.title}, ${p.camera}. Open full size.`);
  $('#heroKicker').textContent='LATEST SIGHTING';$('#heroTitle').textContent=p.camera.toUpperCase();$('#heroMeta').textContent=pretty(p.captured_at);
  if(!heroBound){heroBound=true;pic.addEventListener('click',()=>open(pic.dataset.id));pic.addEventListener('keydown',e=>{if(e.key==='Enter')open(pic.dataset.id)})}
}

function init(data){
  images=(data.length?data:demo).slice().sort((a,b)=>String(b.captured_at).localeCompare(String(a.captured_at)));
  if(data.length)$('#hint').hidden=true;
  stats();hero();refresh();
}

// ---- Owner mode -----------------------------------------------------------
function adminBar(){
  $('#adminBar').hidden=!isOwner();
  $('#ownerLink').textContent=isOwner()?'Owner mode on':'Owner sign-in';
  document.body.classList.toggle('owner',isOwner());
  if(!isOwner())return;
  const n=pending.size;
  if(!$('#adminMsg').dataset.busy)$('#adminMsg').textContent=n?`${n} unsaved change${n>1?'s':''}`:'Owner mode · tap ☆ to favorite, Remove to hide a photo';
  $('#saveEdits').disabled=!n;$('#discardEdits').disabled=!n;
}
function say(msg,busy){const m=$('#adminMsg');m.textContent=msg;if(busy)m.dataset.busy='1';else delete m.dataset.busy}

async function gh(path,opts={}){
  const r=await fetch(API+path,{cache:'no-store',...opts,headers:{Accept:'application/vnd.github+json',Authorization:`Bearer ${token}`,'X-GitHub-Api-Version':'2022-11-28',...(opts.headers||{})}});
  if(!r.ok){const e=new Error(`GitHub said ${r.status}`);e.status=r.status;throw e}
  return r.status===204?null:r.json();
}
const b64=s=>btoa(unescape(encodeURIComponent(s)));
const unb64=s=>decodeURIComponent(escape(atob(s.replace(/\n/g,''))));

async function readEdits(){
  try{const f=await gh(`/contents/${EDITS_PATH}?ref=main`);const j=JSON.parse(unb64(f.content));
    return {sha:f.sha,data:{favorites:j.favorites||[],removed:j.removed||[]}}}
  catch(e){if(e.status===404)return {sha:null,data:{favorites:[],removed:[]}};throw e}
}

async function save(){
  if(!pending.size)return;
  say('Saving…',true);$('#saveEdits').disabled=true;
  for(let attempt=0;attempt<3;attempt++){
    try{
      const {sha,data}=await readEdits();
      const fav=new Set(data.favorites),rem=new Set(data.removed);
      let nf=0,nr=0;
      for(const [id,p] of pending){
        if('fav' in p){p.fav?fav.add(id):fav.delete(id);nf++}
        if('removed' in p){p.removed?rem.add(id):rem.delete(id);nr++}
      }
      const next={favorites:[...fav],removed:[...rem]};
      const parts=[nf&&`${nf} favorite change${nf>1?'s':''}`,nr&&`${nr} removal change${nr>1?'s':''}`].filter(Boolean).join(', ');
      await gh(`/contents/${EDITS_PATH}`,{method:'PUT',body:JSON.stringify({message:`Owner edits: ${parts}`,content:b64(JSON.stringify(next,null,2)+'\n'),branch:'main',...(sha?{sha}:{})})});
      edits=next;pending.clear();stats();hero();refresh();
      say('Saved. The public site updates in about a minute.',false);
      setTimeout(()=>{if(!pending.size)adminBar()},6000);
      return;
    }catch(e){
      if(e.status===409||e.status===422)continue;   // someone else saved first: re-read and retry
      if(e.status===401||e.status===403){say('Your access key was refused. Sign out and sign in with a new key.',false);adminBar();return}
      say('Could not save ('+(e.message||'network error')+'). Try again.',false);adminBar();return;
    }
  }
  say('Could not save because the file kept changing. Try again.',false);adminBar();
}

async function signIn(key){
  const r=await fetch(`https://api.github.com/repos/${REPO}`,{headers:{Accept:'application/vnd.github+json',Authorization:`Bearer ${key}`}});
  if(r.status===401)throw new Error('GitHub did not accept that key. Check that you copied all of it.');
  if(!r.ok)throw new Error(`GitHub answered ${r.status}. Check that the key includes the whitetail-watch repository.`);
  const j=await r.json();
  if(!j.permissions||!j.permissions.push)throw new Error('That key can read the repository but not change it. Give it "Contents: Read and write" permission.');
  token=key;try{localStorage.setItem('ww-owner-token',key)}catch(e){}
  const {data}=await readEdits();edits=data;   // freshest copy, not the cached site file
  stats();hero();refresh();
}
function signOut(){token=null;pending.clear();try{localStorage.removeItem('ww-owner-token')}catch(e){}stats();hero();refresh()}

$('#ownerLink').addEventListener('click',()=>{if(isOwner()){$('#adminBar').scrollIntoView({block:'end'});return}$('#ownerErr').textContent='';$('#tokenInput').value='';$('#ownerDlg').showModal();$('#tokenInput').focus()});
$('#ownerCancel').addEventListener('click',()=>$('#ownerDlg').close());
$('#ownerForm').addEventListener('submit',async e=>{e.preventDefault();const k=$('#tokenInput').value.trim();if(!k){$('#ownerErr').textContent='Paste your access key first.';return}
  $('#ownerGo').disabled=true;$('#ownerErr').textContent='Checking…';
  try{await signIn(k);$('#ownerDlg').close()}catch(err){$('#ownerErr').textContent=err.message}finally{$('#ownerGo').disabled=false}});
$('#saveEdits').addEventListener('click',save);
$('#discardEdits').addEventListener('click',()=>{pending.clear();refresh()});
$('#signOut').addEventListener('click',signOut);
window.addEventListener('beforeunload',e=>{if(pending.size){e.preventDefault();e.returnValue=''}});

// ---- Events ---------------------------------------------------------------
function onTileClick(e){
  const t=e.target.closest('.tile');if(!t)return;
  const act=e.target.closest('[data-act]');
  if(act){e.stopPropagation();const id=t.dataset.id;
    if(act.dataset.act==='fav')setPending(id,'fav',!isFav(id));
    else setPending(id,'removed',!isRemoved(id));
    return}
  open(t.dataset.id);
}
function onTileKey(e){const t=e.target.closest('.tile');if(t&&e.key==='Enter'&&e.target===t)open(t.dataset.id)}
for(const el of [$('#photoGrid'),$('#favStrip')]){el.addEventListener('click',onTileClick);el.addEventListener('keydown',onTileKey)}
$('#typeFilters').addEventListener('click',e=>{const b=e.target.closest('button[data-filter]');if(!b)return;filter=b.dataset.filter;document.querySelectorAll('#typeFilters button').forEach(x=>x.classList.toggle('active',x===b));show()});
$('#camFilters').addEventListener('click',e=>{const b=e.target.closest('button[data-cam]');if(!b)return;cam=b.dataset.cam;document.querySelectorAll('#camFilters button').forEach(x=>x.classList.toggle('active',x===b));show()});
$('#lbFav').addEventListener('click',()=>{const p=openList[cur];if(p)setPending(p.id,'fav',!isFav(p.id))});
$('#lbRemove').addEventListener('click',()=>{const p=openList[cur];if(p)setPending(p.id,'removed',!isRemoved(p.id))});
$('#prev').addEventListener('click',()=>step(-1));
$('#next').addEventListener('click',()=>step(1));
document.addEventListener('keydown',e=>{if(!$('#lightbox').open)return;if(e.key==='ArrowRight')step(1);if(e.key==='ArrowLeft')step(-1)});
let tx=null;$('#lightbox').addEventListener('touchstart',e=>tx=e.touches[0].clientX,{passive:true});
$('#lightbox').addEventListener('touchend',e=>{if(tx===null)return;const dx=e.changedTouches[0].clientX-tx;if(Math.abs(dx)>50)step(dx<0?1:-1);tx=null});
$('#close').addEventListener('click',()=>$('#lightbox').close());
$('#lightbox').addEventListener('click',e=>{if(e.target.id==='lightbox')$('#lightbox').close()});

// ---- Load -----------------------------------------------------------------
const getJSON=u=>fetch(u,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()});
Promise.all([
  getJSON('gallery.json').then(d=>Array.isArray(d.photos)?d.photos:[]).catch(()=>[]),
  getJSON('edits.json').then(d=>({favorites:d.favorites||[],removed:d.removed||[]})).catch(()=>({favorites:[],removed:[]})),
]).then(async ([photos,e])=>{
  edits=e;
  if(isOwner()){try{edits=(await readEdits()).data}catch(err){if(err.status===401){signOut()}}}
  init(photos);
});

(()=>{
const $=id=>document.getElementById(id);
const S=Object.assign({kipas:[0,0,0,0,0],mode:2,usia:0,version:0,channel:'',tRem:0,tState:null,jml:1,hidup:10,mati:5,prt:0,alarm:0,dbw:0,data:{},log:'',suhu:null,min:0,max:0,target:0,ws:false,pend:{}},window.INIT||{});
let ws,tt;
const FAN='<svg viewBox="0 0 24 24" fill="currentColor"><ellipse cx="12" cy="6" rx="3" ry="5"/><ellipse cx="12" cy="6" rx="3" ry="5" transform="rotate(120 12 12)"/><ellipse cx="12" cy="6" rx="3" ry="5" transform="rotate(240 12 12)"/></svg>';
const kunci=()=>S.mode==1||S.mode==3||S.channel==='gagal'||!S.ws;
const send=o=>{if(ws&&ws.readyState===1)ws.send(JSON.stringify(o))};
const set=(p,v)=>send({type:'set_setting',param:p,value:v,version:S.version});
function toast(m){const e=$('toast');e.textContent=m;e.classList.add('on');clearTimeout(tt);tt=setTimeout(()=>e.classList.remove('on'),2600)}

function tema(t){document.documentElement.dataset.theme=t;$('tema').setAttribute('aria-checked',t==='dark');document.cookie='tema='+t+';path=/;max-age=31536000;SameSite=Lax'+(location.protocol==='https:'?';Secure':'');}
$('tema').setAttribute('aria-checked',document.documentElement.dataset.theme==='dark');
$('tema').onclick=()=>tema(document.documentElement.dataset.theme==='dark'?'light':'dark');

function rPill(){
  const [c,t]=!S.ws?['wait','Menghubungkan…']:S.channel==='http'?['ok','Online · HTTP']:S.channel==='serial'?['warn','Online · Serial']:S.channel==='gagal'?['bad','Offline']:['wait','Menunggu data…'];
  $('pill').className='pill '+c;$('pill').textContent=t;$('banner').hidden=S.ws;
}
function rSuhu(){
  const s=Number(S.suhu),ok=S.suhu!==null&&isFinite(s);
  $('suhu').textContent=ok?s.toFixed(1):'--';
  let z='',c='';
  if(ok&&S.max>0){if(s>S.max){z='Panas';c='hot'}else if(s<S.min){z='Dingin';c='cold'}else{z='Normal';c='ok'}}
  $('zona').textContent=z?z+(S.target?' · target '+S.target+'°':''):'';$('zona').className='zona '+c;rNow();
}
function rKipas(){
  const k=kunci(),box=$('kipas');
  if(box.children.length!==5)box.innerHTML=S.kipas.map((_,i)=>`<button class="tile" data-i="${i}"><i class="fan">${FAN}</i><b>${i+1}</b><small></small><em>🔒</em></button>`).join('');
  [...box.children].forEach((t,i)=>{
    const on=S.kipas[i]==1;
    t.className='tile '+(on?'on':'off')+(k?' lock':'')+(S.pend[i]?' pend':'');
    t.querySelector('small').textContent=on?'HIDUP':'MATI';
    t.setAttribute('aria-pressed',on);
  });
  $('kunci').hidden=!k;
  $('kunci').textContent=(!S.ws||S.channel==='gagal')?'🔒 offline':'🔒 mode '+(S.mode==1?'auto':'timer');
}
function opts(sel,list,val,fmt){
  if(sel.dataset.v==val)return;sel.dataset.v=val;
  if(!list.includes(val))list=[...list,val].sort((a,b)=>a-b);
  sel.innerHTML=list.map(v=>`<option value="${v}"${v==val?' selected':''}>${fmt(v)}</option>`).join('');
}
function rTimer(){
  const m=S.mode,show=(m==3||(m==1&&S.timerAktif))&&S.tState;
  $('timer').hidden=!show;if(!show)return;
  const on=S.tState==='ON',tot=on?S.hidup:S.mati*60,r=Math.max(0,S.tRem);
  $('tstat').textContent=on?'Kipas mati dalam':'Kipas hidup dalam';
  $('tcd').textContent=String(r/60|0).padStart(2,'0')+':'+String(r%60).padStart(2,'0');
  $('ring').style.strokeDashoffset=276.5*(1-(tot>0?Math.min(1,Math.max(0,(tot-r)/tot)):0));
  $('ring').classList.toggle('mati',on);
}
function render(){
  rPill();rSuhu();
  [...$('mode').children].forEach(b=>b.classList.toggle('on',b.dataset.v==S.mode));
  $('usia').textContent=S.usia;
  rKipas();
  $('cfg').hidden=S.mode!=3;
  opts($('s-jml'),[1,2,3],S.jml,v=>v+' kipas');
  opts($('s-hdp'),[10,15,20,30,45,60,90,120],S.hidup,v=>v+' detik');
  opts($('s-mti'),[1,2,3,5,10,15,20,30,45,60],S.mati,v=>v+' menit');
  rTimer();rData();
  $('auto').hidden=S.mode!=1;
  if(S.mode==1){const w=uMan??S.usia;if(!busy&&!dirty&&A.usia!==w&&lastTry!==w){lastTry=w;loadAuto(w)}}
}
function apply(d){
  if(saving){const s=saving;saving=null;
    if(d.type==='resync')toast('Data belum tersimpan, coba lagi');
    else{S.data[s.k]=s.v;const i=$('f-'+s.k);i.dataset.dirty='';i.nextElementSibling.hidden=true;toast('Tersimpan')}}
  if(d.kipas){S.kipas=d.kipas;S.pend={}}
  if(d.usia!==undefined)S.usia=d.usia;
  if(d.version!==undefined)S.version=d.version;
  if(d.mode!==undefined)S.mode=d.mode;
  if(d.channel!==undefined)S.channel=d.channel;
  if(d.timer_remaining!==undefined){S.tRem=d.timer_remaining;S.tState=d.timer_state}
  if(d.jumlah_kipas_timer!==undefined)S.jml=d.jumlah_kipas_timer;
  if(d.waktu_hidup!==undefined)S.hidup=d.waktu_hidup;
  if(d.waktu_mati!==undefined)S.mati=d.waktu_mati;
  render();
}

$('kipas').onclick=e=>{
  const t=e.target.closest('.tile');if(!t)return;
  const i=+t.dataset.i;if(S.pend[i])return;
  if(!S.ws)return toast('Belum terhubung ke server');
  if(S.channel==='gagal')return toast('RPi tidak terhubung ke ESP32 (HTTP dan Serial gagal)');
  if(S.mode==1||S.mode==3)return toast('Ganti ke mode Manual atau Panen dulu');
  if(S.prt==1&&!S.kipas[i]&&S.kipas.filter(Number).length>=4){
    t.classList.add('shake');setTimeout(()=>t.classList.remove('shake'),400);
    return toast('Proteksi overload: maksimal 4 kipas hidup');
  }
  S.pend[i]=1;rKipas();
  send({type:'set_kipas',index:i,value:S.kipas[i]?0:1,version:S.version});
  setTimeout(()=>{if(S.pend[i]){delete S.pend[i];rKipas()}},4000);
};
$('mode').onclick=e=>{const b=e.target.closest('button');if(b)set('mode',+b.dataset.v)};
$('u-').onclick=()=>set('usia',Math.max(0,S.usia-1));
$('u+').onclick=()=>set('usia',Math.min(45,S.usia+1));
$('s-jml').onchange=e=>set('jumlah_kipas_timer',+e.target.value);
$('s-hdp').onchange=e=>set('waktu_hidup',+e.target.value);
$('s-mti').onchange=e=>set('waktu_mati',+e.target.value);
document.querySelector('nav').onclick=e=>{
  const b=e.target.closest('button');if(!b)return;
  document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('on',x===b));
  const t=b.dataset.t;['kandang','dashboard','data','kebun'].forEach(x=>$('tab-'+x).hidden=x!==t);
  document.body.classList.toggle('dash',t==='dashboard');navh();
  if(t==='dashboard'&&!$('dash').getAttribute('src'))$('dash').src=LAN?'http://192.168.0.150:8080/api/dashboard':'/api/dashboard';
  if(t==='kebun')dStart();else dStop();
};

// === Tab Data ===
let saving=null;
const FIELD=[
 ['Populasi',[['jumlah_ayam_awal','Jumlah ayam awal','ekor'],['jumlah_ayam_mati','Jumlah ayam mati','ekor'],['jumlah_ayam_dipanen','Jumlah ayam dipanen','ekor']]],
 ['Pakan dan bobot',[['jumlah_pakan_sak','Jumlah pakan','sak'],['bobot_rata_rata','Bobot rata-rata','']]],
 ['Harga',[['harga_kontrak_ayam','Harga kontrak ayam','Rp'],['harga_bibit_ayam','Harga bibit ayam','Rp'],['harga_obat_ayam','Harga obat ayam','Rp'],['harga_pakan_kg','Harga pakan per kg','Rp']]]];
$('fields').innerHTML=FIELD.map(([g,l])=>`<div class="lbl">${g}</div>`+l.map(([k,n,u])=>`<div class="row"><label for="f-${k}">${n}${u?`<small>${u}</small>`:''}</label><input id="f-${k}" data-k="${k}" type="number" inputmode="numeric" step="1" min="0"><button class="ok" data-k="${k}" aria-label="Simpan ${n}" hidden>✓</button></div>`).join('')).join('');
function rData(){
  FIELD.forEach(([,l])=>l.forEach(([k])=>{const i=$('f-'+k);if(!i.dataset.dirty)i.value=S.data[k]??''}));
  $('prt').checked=!!+S.prt;$('alm').checked=!!+S.alarm;$('dbw').checked=!!+S.dbw;
}
function simpan(k){
  const i=$('f-'+k),v=Math.round(Number(i.value));
  if(i.value===''||!isFinite(v)||v<0)return toast('Isi angka 0 atau lebih');
  saving={k,v};set(k,v);
  setTimeout(()=>{if(saving&&saving.k===k){saving=null;toast('Tidak ada respons dari server')}},3000);
}
$('fields').oninput=e=>{const i=e.target;if(!i.dataset.k)return;i.dataset.dirty=String(i.value)!==String(S.data[i.dataset.k]??'')?'1':'';i.nextElementSibling.hidden=!i.dataset.dirty};
$('fields').onclick=e=>{const b=e.target.closest('.ok');if(b)simpan(b.dataset.k)};
$('fields').onkeydown=e=>{if(e.key==='Enter'&&e.target.dataset.k)simpan(e.target.dataset.k)};
function ceklist(){
  const q=`prt_lst=${+$('prt').checked}&flg_dtbs=${+$('dbw').checked}&flg_alrml=${+$('alm').checked}`;
  fetch('/api/ceklist?'+q,{cache:'no-store'}).then(r=>{if(!r.ok)throw 0;S.prt=+$('prt').checked;S.dbw=+$('dbw').checked;S.alarm=+$('alm').checked})
    .catch(()=>{toast('Gagal menyimpan pengaturan');rData()});
}
['prt','alm','dbw'].forEach(id=>$(id).onchange=ceklist);
$('log').textContent=String(S.log||'').replace(/<br\s*\/?>/gi,'\n').trim()||'Belum ada log.';
// Cadangan: kalau server belum mengirim nilai awal, ambil dari /api/mtd
async function muatData(){
  try{
    const m=(await(await fetch('/api/mtd',{cache:'no-store'})).json()).mtd;
    const peta={harga_pakan_kg:0,jumlah_ayam_awal:1,harga_obat_ayam:2,jumlah_ayam_mati:3,harga_bibit_ayam:4,jumlah_pakan_sak:5,harga_kontrak_ayam:6,jumlah_ayam_dipanen:9};
    for(const k in peta)if(S.data[k]==null&&m[peta[k]]!=null)S.data[k]=m[peta[k]];
    rData();
  }catch(e){}
}
muatData();

// === Auto (di tab Kandang) ===
const TMIN=25,TMAX=37,H=360,PAD=14,SPAN=H-2*PAD;
let A={usia:null,rules:[],wajib:[0,0,0,0,0]},dirty=false,uMan=null,busy=false,lastTry=null,nid=100,cur=null,mS='S',pk=[0,0,0,0,0],drag=null;
const yy=t=>PAD+(1-(Math.min(TMAX,Math.max(TMIN,t))-TMIN)/(TMAX-TMIN))*SPAN;
const rt=r=>r.mode==='T'?r.suhu_batas:r.suhu;
const sett=(r,t)=>{t=Math.round(Math.min(TMAX,Math.max(TMIN,t))*10)/10;if(r.mode==='T')r.suhu_batas=t;else r.suhu=t};
const dots=r=>r.mode==='S'?r.kipas.map(Boolean):Array.from({length:5},(_,i)=>i<r.jumlah_kipas);
const mark=()=>{dirty=true;$('adirty').hidden=false};
$('tks').innerHTML=Array.from({length:TMAX-TMIN+1},(_,i)=>{const t=TMIN+i;return `<span class="tk${t%5==0?' m':''}" style="top:${yy(t)}px">${t}°</span>`}).join('');
function chips(box,arr,fn){
  box.innerHTML=arr.map((v,i)=>`<button class="chip" data-i="${i}" aria-pressed="${!!v}">K${i+1}</button>`).join('');
  box.onclick=e=>{const b=e.target.closest('.chip');if(!b)return;const i=+b.dataset.i;arr[i]=arr[i]?0:1;b.setAttribute('aria-pressed',!!arr[i]);if(fn)fn()};
}
function rHd(){
  $('hds').innerHTML=A.rules.map(r=>`<div class="hd ${r.mode}" data-id="${r.id}" style="top:${yy(rt(r))}px">${r.mode==='T'?'Timer':'Suhu'}</div><div class="inf" data-id="${r.id}" style="top:${yy(rt(r))}px"><span class="tag">${rt(r).toFixed(1)}°</span><span class="dots">${dots(r).map(o=>`<i class="${o?'on':''}"></i>`).join('')}</span></div>`).join('');
}
function rNow(){
  const s=Number(S.suhu),ok=S.suhu!==null&&isFinite(s);
  $('now').hidden=$('nowl').hidden=!ok;if(!ok)return;
  $('now').style.top=$('nowl').style.top=yy(s)+'px';$('nowl').textContent='Suhu '+s.toFixed(1)+'°';
}
const hds=$('hds');
hds.addEventListener('pointerdown',e=>{const h=e.target.closest('.hd');if(!h)return;const r=A.rules.find(x=>x.id==h.dataset.id);drag={r,h,y0:e.clientY,t0:rt(r),mv:false};h.setPointerCapture(e.pointerId);e.preventDefault()});
hds.addEventListener('pointermove',e=>{
  if(!drag)return;const dy=e.clientY-drag.y0;if(Math.abs(dy)>6)drag.mv=true;if(!drag.mv)return;
  sett(drag.r,drag.t0-dy/SPAN*(TMAX-TMIN));
  const top=yy(rt(drag.r))+'px',inf=hds.querySelector(`.inf[data-id="${drag.r.id}"]`);
  drag.h.style.top=top;inf.style.top=top;inf.querySelector('.tag').textContent=rt(drag.r).toFixed(1)+'°';mark();
});
hds.addEventListener('pointerup',()=>{if(!drag)return;const d=drag;drag=null;if(!d.mv)openSheet(d.r)});
hds.addEventListener('pointercancel',()=>{drag=null});

function sheetMode(m){mS=m;[...$('sm').children].forEach(b=>b.classList.toggle('on',b.dataset.m===m));$('p-S').hidden=m!=='S';$('p-T').hidden=m!=='T'}
function openSheet(r){
  cur=r;sheetMode(r.mode);$('p-t').value=rt(r);
  pk=r.mode==='S'?[...r.kipas]:[1,0,0,0,0];chips($('p-f'),pk);
  const T=r.mode==='T'?r:{map_min:25,map_max:35,jumlah_kipas:1,on_min:10,on_max:60,off_min:5,off_max:30};
  $('p-mn').value=T.map_min;$('p-mx').value=T.map_max;$('p-j').value=T.jumlah_kipas;
  $('p-a').value=T.on_min;$('p-b').value=T.on_max;$('p-c').value=T.off_min;$('p-d').value=T.off_max;
  $('ov').hidden=$('sheet').hidden=false;
}
const closeSheet=()=>{$('ov').hidden=$('sheet').hidden=true;cur=null};
$('sm').onclick=e=>{const b=e.target.closest('button');if(b)sheetMode(b.dataset.m)};
$('p-no').onclick=$('ov').onclick=closeSheet;
$('p-del').onclick=()=>{A.rules=A.rules.filter(x=>x!==cur);mark();closeSheet();rHd()};
$('p-ok').onclick=()=>{
  const n=id=>Number($(id).value),t=Math.min(TMAX,Math.max(TMIN,n('p-t')||30));
  if(mS==='S'){Object.assign(cur,{mode:'S',suhu:t,kipas:[...pk]});delete cur.suhu_batas}
  else{Object.assign(cur,{mode:'T',suhu_batas:t,map_min:n('p-mn'),map_max:n('p-mx'),jumlah_kipas:Math.min(5,Math.max(1,n('p-j')|0)),on_min:n('p-a')|0,on_max:n('p-b')|0,off_min:n('p-c')|0,off_max:n('p-d')|0});delete cur.suhu;delete cur.kipas}
  mark();closeSheet();rHd();
};
$('addr').onclick=()=>{
  if(A.rules.length>=5)return toast('Maksimal 5 aturan');
  const r={id:nid++,mode:'S',suhu:32,kipas:[1,0,0,0,0]};A.rules.push(r);mark();rHd();openSheet(r);
};
$('asave').onclick=async()=>{
  if(A.usia==null)return toast('Aturan belum dimuat');
  const f=r=>r.mode==='S'?`S-${Math.round(r.suhu*10)}-${r.kipas.map(v=>v?1:0).join('')}`:`T-${[Math.round(r.suhu_batas*10),r.jumlah_kipas,Math.round(r.map_min*10),Math.round(r.map_max*10),r.on_min,r.on_max,r.off_min,r.off_max].join('-')}`;
  const so=[...A.rules].sort((a,b)=>a.mode===b.mode?rt(a)-rt(b):(a.mode==='T'?-1:1));
  const out=[A.usia,A.wajib.map(v=>v?1:0).join(''),...Array.from({length:5},(_,i)=>so[i]?f(so[i]):'N')];
  try{const d=await(await fetch('/api/atur_auto?tulis='+encodeURIComponent(out.join(',')))).json();
    if(d.status!=='OK')throw 0;dirty=false;$('adirty').hidden=true;toast('Aturan usia '+A.usia+' tersimpan');
  }catch(e){toast('Gagal menyimpan aturan')}
};
async function loadAuto(u){
  busy=true;
  try{const d=await(await fetch('/api/auto_konf?usia='+u,{cache:'no-store'})).json();
    A={usia:d.usia,wajib:d.wajib,rules:d.rules};dirty=false;$('adirty').hidden=true;
    $('ausia').textContent=A.usia;chips($('wajib'),A.wajib,mark);rHd();
  }catch(e){toast('Gagal memuat aturan auto')}
  busy=false;
}
const gotoU=u=>{if(dirty)return toast('Simpan dulu perubahan aturan ini');uMan=Math.min(45,Math.max(0,u));render()};
$('a-').onclick=()=>gotoU((uMan??S.usia)-1);
$('a+').onclick=()=>gotoU((uMan??S.usia)+1);

// === Tab Kebun: LAN = langsung ke ESP, selain itu lewat proxy Pi ===
const LAN=/^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(location.hostname)||location.hostname.endsWith('.local');
const IP=(window.INIT||{}).ip||{};
const wsurl=d=>(LAN&&IP[d])?`ws://${IP[d]}/ws`:`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/ws/dev/${d}`;
const DV=[
 {id:'pompa',nama:'Pompa Sendang',g:[['',[['on','Pompa']]]]},
 {id:'kebun',nama:'Air Kebun Belakang',g:[['',[['on','Air kebun']]]]},
 {id:'pupuk',nama:'Mesin Pupuk',g:[['Pompa nutrisi',[['A','Pupuk A'],['B','Pupuk B'],['C','Pupuk C']]],['Pengaduk dan penyiram benih',[['P','Pengaduk'],['S','Siram benih']]]]}];
const D={pompa:{on:null},kebun:{on:null},pupuk:{A:null,B:null,C:null,P:null,S:null}},W={};
let dAktif=false;
const cardDev=v=>`<div class="card"><div class="dh"><span class="lbl">${v.nama}</span><span class="dst" id="st-${v.id}">Menghubungkan…</span></div>`
  +v.g.map(([gn,ts])=>(gn?`<div class="lbl" style="margin:10px 0 6px">${gn}</div>`:'')+`<div class="dgrid">`+ts.map(([k,n])=>`<button class="dt na" data-d="${v.id}" data-k="${k}"><b>${n}</b><small>...</small></button>`).join('')+`</div>`).join('')
  +((LAN&&IP[v.id])?`<a class="dl" href="http://${IP[v.id]}/set">Buka halaman perangkat</a>`:'')+`</div>`;
$('dev').innerHTML=`<div class="dpair">${cardDev(DV[0])}${cardDev(DV[1])}</div>`+cardDev(DV[2]);
function rDev(){document.querySelectorAll('.dt').forEach(b=>{const v=D[b.dataset.d][b.dataset.k];b.className='dt '+(v===null?'na':v?'on':'off');b.querySelector('small').textContent=v===null?'...':v?'NYALA':'MATI'})}
function dst(d,t,c){const e=$('st-'+d);e.textContent=t+(c==='ok'&&!LAN?' (via Pi)':'');e.className='dst '+c}
function dmsg(d,t){
  if(d==='pupuk'){try{const j=JSON.parse(t);j.pompa.forEach(p=>D.pupuk[p.id]=p.nyala);D.pupuk.P=j.pengaduk.nyala;D.pupuk.S=j.solenoid.nyala}catch(e){return}}
  else D[d].on=t==='1';
  rDev();
}
function dconn(d){
  if(!dAktif||(W[d]&&W[d].readyState<2))return;
  let w;try{w=new WebSocket(wsurl(d))}catch(e){return setTimeout(()=>dconn(d),4000)}
  W[d]=w;
  w.onopen=()=>dst(d,'Terhubung','ok');
  w.onmessage=e=>dmsg(d,e.data);
  w.onclose=()=>{for(const k in D[d])D[d][k]=null;rDev();dst(d,'Terputus, menyambung ulang…','bad');setTimeout(()=>dconn(d),2000)};
  w.onerror=()=>w.close();
}
const dStart=()=>{dAktif=true;DV.forEach(v=>dconn(v.id))};
const dStop=()=>{dAktif=false;Object.values(W).forEach(w=>w.close())};
$('dev').onclick=e=>{
  const b=e.target.closest('.dt');if(!b)return;
  const d=b.dataset.d,k=b.dataset.k,w=W[d],v=D[d][k];
  if(!w||w.readyState!==1||v===null)return toast('Perangkat belum terhubung');
  w.send(d==='pupuk'?k+':'+(v?'off':'on'):(v?'off':'on'));
};
rDev();

// === Sistem: mulai ulang layanan / reboot (tekan dua kali) ===
const AKSI={
  restart:{url:'/api/sistem/restart-service',pesan:'Sistem dimulai ulang, halaman tersambung lagi sebentar lagi…'},
  reboot:{url:'/api/sistem/reboot',pesan:'Raspberry Pi akan reboot, tunggu 1–2 menit…'}};
const armed={};
$('sistem').onclick=async e=>{
  const b=e.target.closest('button[data-aksi]');if(!b||b.disabled)return;
  const k=b.dataset.aksi,teks=b.dataset.teks;
  if(!armed[k]){
    armed[k]=setTimeout(()=>{delete armed[k];b.classList.remove('armed');b.textContent=teks},4000);
    b.classList.add('armed');b.textContent='Tekan lagi untuk konfirmasi';return;
  }
  clearTimeout(armed[k]);delete armed[k];b.classList.remove('armed');b.disabled=true;b.textContent=teks;
  try{
    const r=await fetch(AKSI[k].url,{method:'POST'});
    const d=await r.json().catch(()=>({}));
    if(!r.ok)throw new Error(d.detail||('HTTP '+r.status));
    toast(AKSI[k].pesan);
  }catch(err){toast('Gagal: '+err.message)}
  setTimeout(()=>{b.disabled=false},10000);
};

function conn(){
  ws=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/api/ws/kipas');
  ws.onopen=()=>{S.ws=true;S.version=0;render()};
  ws.onmessage=e=>apply(JSON.parse(e.data));
  ws.onclose=()=>{S.ws=false;render();setTimeout(conn,3000)};
  ws.onerror=()=>ws.close();
}
async function poll(){
  try{const k=(await(await fetch('/api/',{cache:'no-store'})).json()).kpa;
    S.target=k[5];S.min=k[6];S.max=k[7];S.suhu=k[k.length-1];S.timerAktif=!!Number(k[13]);rSuhu();rTimer();}catch(e){}
}
setInterval(()=>{if(S.tRem>0){S.tRem--;rTimer()}},1000);
const navh=()=>document.documentElement.style.setProperty('--navh',document.querySelector('nav').offsetHeight+'px');
navh();addEventListener('resize',navh);
render();conn();poll();setInterval(poll,5000);
})();
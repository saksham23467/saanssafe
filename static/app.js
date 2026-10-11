const $=s=>document.querySelector(s);
const CATS=[["Good","#009933"],["Satisfactory","#58A618"],["Moderate","#E6C700"],["Poor","#F28C00"],["Very Poor","#E02020"],["Severe","#7E0023"]];
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const ROUTES={"":"single","districts":"multi","alerts":"alerts","about":"about"};
function route(){const k=location.hash.replace(/^#\/?/,"");const v=ROUTES[k]||"single";
  document.querySelectorAll(".tab").forEach(x=>{const on=x.dataset.view===v;x.classList.toggle("on",on);on?x.setAttribute("aria-current","page"):x.removeAttribute("aria-current")});
  document.querySelectorAll(".view").forEach(s=>s.hidden=s.id!==v);window.scrollTo(0,0)}
window.addEventListener("hashchange",route);route();

$("#f").onsubmit=async e=>{e.preventDefault();const b=e.submitter||$("#f .primary");b.disabled=true;b.textContent="Checking the air…";
  $("#err").hidden=true;$("#out").hidden=true;const sk=document.createElement("div");sk.className="skeleton";$("#f").after(sk);
  try{const r=await fetch("/api/plan",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({place:$("#place").value,school:$("#school").value,start:+$("#start").value,end:+$("#end").value})});
    const d=await r.json();if(!r.ok)throw new Error(d.detail||"Something went wrong");render(d)}
  catch(x){$("#err").textContent=x.message;$("#err").hidden=false}finally{sk.remove();b.disabled=false;b.textContent="Get today's plan"}};

function render(d){const p=d.plan,c=p.current,k=c.category;const h=$("#hero");
  h.style.setProperty("--cat",k.color);h.style.setProperty("--catfg",k.fg);
  const idx=CATS.findIndex(x=>x[0]===k.name);
  h.innerHTML=`<div class="eyebrow">${esc(d.label)} · CPCB AQI (24-h avg)</div><div class="aqi">${c.aqi}</div>
   <span class="catbadge">${esc(k.name)}</span><div class="meta">PM2.5 ${c.pm2_5} µg/m³ · PM10 ${c.pm10} µg/m³ · dominant ${c.dominant}${p.max_feels_like!=null?` · feels like up to ${Math.round(p.max_feels_like)}°C`:""}</div>
   <div class="scale">${CATS.map((x,i)=>`<i style="background:${x[1]}" class="${i===idx?"me":""}" title="${x[0]}"></i>`).join("")}</div>
   <p class="health"><b>CPCB health note:</b> ${esc(k.health)}</p>`;
  $("#headline").closest(".decision").className="decision status-"+p.status;$("#headline").closest(".decision").style.setProperty("--cat",k.color);
  $("#headline").textContent=p.headline;$("#reason").textContent=`Air quality in ${d.label.split(",")[0]} is ${k.name} (AQI ${c.aqi})`+(p.safe_window?`, safest outdoors ${pad(p.safe_window[0])}:00–${pad(p.safe_window[1])}:00.`:", with no safe outdoor window in school hours.");$("#actions").innerHTML=p.actions.map(a=>`<li>${esc(a)}</li>`).join("");
  $("#charttitle").textContent=`Air quality on ${new Date(p.day).toLocaleDateString("en-IN",{weekday:"long",day:"numeric",month:"short"})}`;
  const w=$("#window");if(p.safe_window){w.className="pill";w.textContent=`Safe outdoor window ${pad(p.safe_window[0])}:00–${pad(p.safe_window[1])}:00`}else{w.className="pill no";w.textContent="No safe outdoor window in school hours"}
  chart(p.hours,p.safe_window);outlook(d.outlook||[]);
  $("#en").textContent=d.notice.english;$("#hi").textContent=d.notice.hindi;
  const msg=d.notice.english+"\n\n"+d.notice.hindi;$("#wa").href="https://wa.me/?text="+encodeURIComponent(msg);
  $("#copy").onclick=async()=>{await navigator.clipboard.writeText(msg).catch(()=>{});$("#copy").textContent="Copied";setTimeout(()=>$("#copy").textContent="Copy",1500)};
  $("#summary").textContent=d.summary;$("#mode").textContent=d.mode==="agent"?"· Strands agent":"· deterministic mode (no LLM)";
  $("#out").hidden=false;}
const pad=n=>String(n).padStart(2,"0");

function chart(hs,win){const W=960,H=230,L=36,B=26,T=10,n=hs.length;if(!n){$("#chart").innerHTML="<p class=note>No hourly data.</p>";return}
  const mx=Math.max(220,...hs.map(x=>x.aqi))*1.1,bw=(W-L)/n,y=v=>T+(H-T-B)*(1-v/mx);let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Hourly AQI chart">`;
  [[0,100,"#009933"],[100,200,"#E6C700"],[200,300,"#F28C00"],[300,400,"#E02020"],[400,600,"#7E0023"]].forEach(([a,b,c])=>{if(a<mx)s+=`<rect x="${L}" y="${y(Math.min(b,mx))}" width="${W-L}" height="${y(a)-y(Math.min(b,mx))}" fill="${c}" opacity=".07"/>`});
  [100,200,300,400].filter(v=>v<mx).forEach(v=>s+=`<line x1="${L}" x2="${W}" y1="${y(v)}" y2="${y(v)}" stroke="#ddd" stroke-dasharray="3 3"/><text x="${L-6}" y="${y(v)+4}" font-size="11" text-anchor="end" fill="#888">${v}</text>`);
  hs.forEach((x,i)=>{const sch=x.school,inwin=win&&x.hour>=win[0]&&x.hour<win[1];
    if(inwin)s+=`<rect x="${L+i*bw}" y="${T}" width="${bw}" height="${H-T-B}" fill="#0d7a3a" opacity=".08"/>`;
    s+=`<rect x="${L+i*bw+2}" y="${y(x.aqi)}" width="${bw-4}" height="${y(0)-y(x.aqi)}" rx="2" fill="${x.color}" opacity="${sch?1:.35}"><title>${pad(x.hour)}:00 · AQI ${x.aqi} ${x.category}${x.feels_like!=null?" · feels "+Math.round(x.feels_like)+"°C":""}</title></rect>`;
    if(x.hour%3===0)s+=`<text x="${L+i*bw+bw/2}" y="${H-8}" font-size="11" text-anchor="middle" fill="#666">${pad(x.hour)}</text>`});
  $("#chart").innerHTML=s+"</svg>";}

function outlook(o){$("#outlook").innerHTML=o.map(d=>`<div class="day ${d.indoor?"indoor":""}"><b>${d.dow}</b><small>${d.date.slice(8)}/${d.date.slice(5,7)}</small>
  <span class="dot" style="background:${d.color};color:${d.fg}">${d.aqi??"–"}</span><small>${esc(d.category)}</small>
  ${d.indoor?'<div class="tag">Plan indoor</div>':'<small>&nbsp;</small>'}<small>${d.feels_max!=null?"feels "+Math.round(d.feels_max)+"°C":""}</small></div>`).join("")}

$("#mf").onsubmit=async e=>{e.preventDefault();const b=$("#mf .primary");b.disabled=true;b.textContent="Ranking…";$("#mout").innerHTML='<div class="skeleton"></div>';
  try{const r=await fetch("/api/rank",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({places:$("#places").value.split("\n")})});const rows=await r.json();
  $("#mout").innerHTML=`<table><thead><tr><th>#</th><th>Locality</th><th>AQI now</th><th class="hide-sm">Peak in school hours</th><th>Decision</th><th class="hide-sm">Outdoor window</th></tr></thead><tbody>${
   rows.map((x,i)=>x.error?`<tr><td>${i+1}</td><td>${esc(x.query)}</td><td colspan=4>${esc(x.error)}</td></tr>`:`<tr><td>${i+1}</td><td>${esc(x.label)}</td>
   <td><span class="chip" style="background:${x.color};color:${x.fg}">${x.aqi} · ${esc(x.category)}</span></td><td class="hide-sm">${x.peak}</td>
   <td><b>${esc(x.headline)}</b></td><td class="hide-sm">${x.window?pad(x.window[0])+":00–"+pad(x.window[1])+":00":"None"}</td></tr>`).join("")}</tbody></table>
   <p class="note">Ranked by recommended action level, then by forecast peak AQI during school hours.</p>`}
  catch(x){$("#mout").innerHTML=`<div class="err">${esc(x.message)}</div>`}finally{b.disabled=false;b.textContent="Rank schools"}};

// ---------------------------------------------------------------- voice (Web Speech API)
const synth=window.speechSynthesis;let voices=[];
const loadVoices=()=>{voices=synth?synth.getVoices():[]};if(synth){loadVoices();synth.onvoiceschanged=loadVoices}
const pickVoice=lang=>voices.find(v=>v.lang.replace("_","-").toLowerCase()===lang.toLowerCase())||voices.find(v=>v.lang.toLowerCase().startsWith(lang.slice(0,2)));
function hint(t){const h=$("#voicehint");h.textContent=t;h.hidden=!t}
function stopSpeak(){if(synth)synth.cancel();document.querySelectorAll(".speak").forEach(s=>{s.classList.remove("on");s.querySelector(".stop").hidden=true})}
document.querySelectorAll(".speak").forEach(sp=>{
  sp.querySelector(".play").onclick=()=>{
    if(!synth||!window.SpeechSynthesisUtterance){hint("Your browser doesn't support read-aloud. Try Chrome or Edge.");return}
    stopSpeak();loadVoices();const lang=sp.dataset.lang,u=new SpeechSynthesisUtterance($("#"+sp.dataset.src).textContent);
    u.lang=lang;u.rate=.95;const v=pickVoice(lang);
    if(v){u.voice=v;hint("")}else hint(lang==="hi-IN"?"No Hindi voice installed on this device, so your browser's default voice is used. Install a Hindi (India) voice in your OS speech settings, or use Chrome/Android, for natural Hindi.":"No English (India) voice found, so the default voice is used.");
    u.onend=u.onerror=()=>{sp.classList.remove("on");sp.querySelector(".stop").hidden=true};
    sp.classList.add("on");sp.querySelector(".stop").hidden=false;synth.speak(u)};
  sp.querySelector(".stop").onclick=stopSpeak});

// ---------------------------------------------------------------- morning alerts
const api=async(u,o={})=>{const r=await fetch(u,{headers:{"Content-Type":"application/json"},...o});const d=await r.json();
  if(!r.ok)throw new Error(Array.isArray(d.detail)?d.detail.map(x=>x.msg).join("; "):d.detail||"Something went wrong");return d};
async function loadSubs(){const s=await api("/api/alerts/subscriptions");
  $("#subcount").textContent=s.length?`${s.length} school${s.length>1?"s":""} get the 7 AM plan`:"No schools yet";
  $("#subs").innerHTML=s.map(x=>`<li><span><b>${esc(x.school)}</b> · ${esc(x.place)}<br><small>${x.contact?esc(x.contact_type)+": "+esc(x.contact):"no contact (outbox only)"}</small></span>
    <button class="ghost sm" data-del="${esc(x.id)}">Remove</button></li>`).join("");
  document.querySelectorAll("[data-del]").forEach(b=>b.onclick=async()=>{await api("/api/alerts/subscriptions/"+b.dataset.del,{method:"DELETE"});loadSubs()})}
async function loadOutbox(){const o=await api("/api/alerts/outbox");
  $("#outbox").innerHTML=o.length?o.slice(0,8).map(m=>`<div class="obx"><b>${esc(m.subject)}</b><br><small>${esc(m.created_at)} · ${esc(m.channel)} · to ${esc(m.to||"outbox")}</small></div>`).join(""):'<p class="note">Nothing yet.</p>'}
$("#sf").onsubmit=async e=>{e.preventDefault();$("#serr").hidden=true;
  try{await api("/api/alerts/subscribe",{method:"POST",body:JSON.stringify({school:$("#sschool").value,place:$("#splace").value,contact:$("#scontact").value})});
    $("#sschool").value=$("#splace").value=$("#scontact").value="";loadSubs()}catch(x){$("#serr").textContent=x.message;$("#serr").hidden=false}};
$("#runnow").onclick=async()=>{const b=$("#runnow");b.disabled=true;b.textContent="Running the 7 AM job…";$("#aout").innerHTML='<div class="skeleton"></div>';
  try{const r=await api("/api/alerts/run-now",{method:"POST"});
    $("#aout").innerHTML=`<p class="note">Job ran ${esc(r.ran_at)} · schedule <code>${esc(r.schedule)}</code> (${esc(r.schedule_ist)}) · channel ${esc(r.channel)} · ${r.sent}/${r.count} delivered</p>`+
     (r.count?"":'<div class="err">Subscribe a school first.</div>')+
     r.alerts.map(a=>a.error?`<article class="card"><b>${esc(a.school)}</b>: ${esc(a.error)}</article>`:
     `<article class="card alert" style="--c:${a.color}"><div class="eyebrow">7:00 AM alert · ${esc(a.place)}</div><h3>${esc(a.subject)}</h3>
      <p class="mail">To: <b>${esc(a.to||"outbox")}</b> ${a.contact_type?"("+esc(a.contact_type)+")":""}</p><pre>${esc(a.body)}</pre></article>`).join("");
    loadOutbox()}catch(x){$("#aout").innerHTML=`<div class="err">${esc(x.message)}</div>`}finally{b.disabled=false;b.textContent="Preview tomorrow's 7 AM alert"}};
loadSubs().catch(()=>{});loadOutbox().catch(()=>{});

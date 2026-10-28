function missionCardHTML(m){
  const id=Number(m.id);
  return `<article class="mission-card" data-id="${id}">
    <div class="mission-card-top"><span class="mission-type">${escapeHTML(m.skill)} <i>·</i> مأموریت هوشمند</span><span class="difficulty">${escapeHTML(m.difficulty)}</span></div>
    <div class="mission-symbol symbol-purple">✳</div><h3>${escapeHTML(m.title)}</h3><p>${escapeHTML(m.description)}</p>
    <div class="mission-footer"><span class="xp-label">✳ ${Number(m.xp)} XP</span><div class="mission-actions"><button class="complete-button" data-complete="${id}">تکمیل مأموریت <span>←</span></button><button class="mission-delete-button" type="button" data-delete-mission="${id}" aria-label="حذف مأموریت" title="حذف مأموریت">حذف ×</button></div></div>
  </article>`;
}
function updateMissionCounts(data){
  const total=document.querySelector("#total-count"), completed=document.querySelector("#completed-count"), xp=document.querySelector("#total-xp");
  if(total && data.total_count!==undefined) total.textContent=data.total_count;
  if(completed && data.completed_count!==undefined) completed.textContent=data.completed_count;
  if(xp && data.xp!==undefined) xp.textContent=data.xp;
  const bar=document.querySelector(".stat-card .stat-progress span");
  if(bar){const t=Number(total?.textContent||0),d=Number(completed?.textContent||0);bar.style.width=(t?Math.round(d/t*100):0)+"%";}
  const heading=document.querySelector("#missions h2 .muted");
  if(heading && total) heading.textContent=`(${total.textContent})`;
}
async function completeMission(button){
  if(button.disabled)return;button.disabled=true;
  try{
    const data=await postJSON("/api/mission/complete/",{id:button.dataset.complete});
    const card=button.closest(".mission-card");card.classList.add("mission-complete");
    button.outerHTML='<span class="done-label">✓ تکمیل شد</span>';updateMissionCounts(data);
    try { const next=await postJSON("/api/mission/auto/"); if(next.created){document.querySelector("#mission-grid")?.insertAdjacentHTML("afterbegin",missionCardHTML(next));updateMissionCounts({total_count:next.total_count});} }
    catch(_ignored) {  }
  }catch(e){alert(e.message);button.disabled=false;}
}
document.addEventListener("click",async event=>{
  const complete=event.target.closest("[data-complete]");if(complete){completeMission(complete);return;}
  const del=event.target.closest("[data-delete-mission]");if(!del)return;
  if(!confirm("این مأموریت برای همیشه از فضای کارت حذف شود؟"))return;
  del.disabled=true;
  try{
    const result=await postJSON(`/api/mission/${Number(del.dataset.deleteMission)}/delete/`,{});
    del.closest(".mission-card")?.remove();updateMissionCounts(result);
    const grid=document.querySelector("#mission-grid");if(grid && !grid.querySelector(".mission-card"))grid.innerHTML='<div class="mission-empty">مأموریتی باقی نمانده؛ Nexora به‌زودی قدم بعدی را پیشنهاد می‌دهد.</div>';
  }catch(e){alert(e.message);del.disabled=false;}
});
const newButton=document.querySelector("#new-mission");
if(newButton)newButton.addEventListener("click",async()=>{
  newButton.disabled=true;newButton.classList.add("loading");const original=newButton.innerHTML;newButton.innerHTML="در حال ساخت مأموریت...";
  try{const m=await postJSON("/api/mission/new/");document.querySelector("#mission-grid")?.insertAdjacentHTML("afterbegin",missionCardHTML(m));updateMissionCounts({total_count:m.total_count||Number(document.querySelector("#total-count")?.textContent||0)+1});if(m.notice)alert(m.notice);}
  catch(e){alert(e.message);}
  finally{newButton.disabled=false;newButton.classList.remove("loading");newButton.innerHTML=original;}
});
const missionGrid=document.querySelector("#mission-grid");
if(missionGrid && Number(missionGrid.dataset.activeCount||0)<6){
  postJSON("/api/mission/auto/").then(m=>{if(m.created){missionGrid.insertAdjacentHTML("afterbegin",missionCardHTML(m));missionGrid.dataset.activeCount=String(m.active_count||0);updateMissionCounts({total_count:m.total_count});}}).catch(()=>{});
}

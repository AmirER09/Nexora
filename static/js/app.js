function getCookie(name){let cookieValue=null;if(document.cookie&&document.cookie!==""){for(const cookie of document.cookie.split(";")){const c=cookie.trim();if(c.substring(0,name.length+1)===(name+"=")){cookieValue=decodeURIComponent(c.substring(name.length+1));break;}}}return cookieValue;}
async function postJSON(url,data={}){const response=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":getCookie("csrftoken")||""},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw new Error(result.error||"درخواست ناموفق بود.");return result;}
function escapeHTML(value){return String(value).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
document.addEventListener("DOMContentLoaded",()=>{
  document.querySelectorAll(".interest-option input[type=checkbox]").forEach(input=>{
    const card=input.closest(".interest-option");
    if(!card) return;
    const sync=()=>{card.classList.toggle("selected",input.checked);card.setAttribute("aria-checked",String(input.checked));};
    sync();
    input.addEventListener("change",sync);
    card.addEventListener("keydown",event=>{
      if((event.key==="Enter"||event.key===" ")&&event.target===card){event.preventDefault();input.checked=!input.checked;input.dispatchEvent(new Event("change",{bubbles:true}));}
    });
  });
});

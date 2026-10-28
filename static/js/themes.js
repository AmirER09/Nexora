(function(){
  const allowed=['aurora','ocean','rose','emerald','sunset'];
  const select=document.getElementById('theme-select');
  const serverTheme=document.documentElement.dataset.theme||'aurora';
  function apply(theme,save){
    if(!allowed.includes(theme))theme='aurora';
    document.documentElement.dataset.theme=theme;
    if(select)select.value=theme;
    if(save){
      try{localStorage.setItem('nexora-theme',theme)}catch(e){}
      const token=document.querySelector('input[name=csrfmiddlewaretoken]');
      if(token){
        fetch('/settings/theme/',{
          method:'POST',
          headers:{'Content-Type':'application/x-www-form-urlencoded','X-CSRFToken':token.value},
          body:new URLSearchParams({theme:theme,next:location.pathname})
        }).catch(()=>{});
      }
    }
  }
  apply(serverTheme,false);
  if(select)select.addEventListener('change',()=>apply(select.value,true));

  const shell=document.querySelector('.app-shell');
  const toggle=document.getElementById('mobile-menu-button');
  function setMenu(open){
    if(!shell||!toggle)return;
    shell.classList.toggle('sidebar-open',open);
    toggle.setAttribute('aria-expanded',String(open));
    toggle.setAttribute('aria-label',open?'بستن منو':'باز کردن منو');
    toggle.textContent=open?'✕':'☰';
  }
  if(shell&&toggle){
    toggle.addEventListener('click',()=>setMenu(!shell.classList.contains('sidebar-open')));
    document.querySelectorAll('.sidebar .nav-link').forEach(a=>a.addEventListener('click',()=>setMenu(false)));
    document.addEventListener('click',event=>{
      if(!shell.classList.contains('sidebar-open'))return;
      if(event.target===shell||(!event.target.closest('.sidebar')&&!event.target.closest('#mobile-menu-button')))setMenu(false);
    });
    document.addEventListener('keydown',event=>{if(event.key==='Escape')setMenu(false)});
  }
})();

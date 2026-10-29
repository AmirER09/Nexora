(() => {
  const form = document.querySelector('#chat-form');
  const input = document.querySelector('#chat-input');
  const box = document.querySelector('#chat-messages');
  if (!form || !input || !box) return;
  const sendButton = form.querySelector('button[type="submit"]');
  const scrollToLatest = () => { box.scrollTop = box.scrollHeight; };

  function appendMessage(role, text, pending = false) {
    const article = document.createElement('article');
    article.className = `chat-message ${role}${pending ? ' is-pending' : ''}`;
    const face = document.createElement('div');
    face.className = `chat-face${role === 'assistant' ? ' mentor-face' : ''}`;
    face.textContent = role === 'user' ? 'ش' : 'n.';
    const body = document.createElement('div'); body.className = 'message-body';
    const name = document.createElement('div'); name.className = 'message-name'; name.textContent = role === 'user' ? 'تو' : 'Nexora';
    if (role === 'assistant') { const label = document.createElement('span'); label.textContent = 'منتور هوشمند'; name.appendChild(label); }
    const message = document.createElement('div'); message.className = 'message-text'; message.textContent = text;
    body.append(name, message); article.append(face, body); box.appendChild(article); scrollToLatest();
    return { article, message };
  }

  async function sendMessage(value) {
    const text = value.trim();
    if (!text || sendButton.disabled) return;
    input.value = ''; input.style.height = 'auto';
    appendMessage('user', text);
    const pending = appendMessage('assistant', 'دارم پیام تو رو بررسی می‌کنم…', true);
    sendButton.disabled = true; input.disabled = true; form.classList.add('is-sending');
    try {
      if (typeof postJSON !== 'function') throw new Error('ارتباط با سرویس گفتگو آماده نیست. صفحه رو یک‌بار تازه‌سازی کن.');
      const data = await postJSON('/api/chat/', { message: text });
      pending.message.textContent = data.reply || 'پاسخی دریافت نشد. دوباره امتحان کن.';
      pending.article.classList.remove('is-pending');
    } catch (error) {
      pending.article.classList.remove('is-pending'); pending.article.classList.add('message-error');
      pending.message.textContent = error.message || 'ارسال پیام انجام نشد. اتصال رو بررسی کن و دوباره تلاش کن.';
    } finally {
      sendButton.disabled = false; input.disabled = false; form.classList.remove('is-sending'); input.focus(); scrollToLatest();
    }
  }
  form.addEventListener('submit', event => { event.preventDefault(); sendMessage(input.value); });
  input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); form.requestSubmit(); } });
  input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 150)}px`; });
  document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => { input.value = button.dataset.prompt || ''; input.focus(); input.dispatchEvent(new Event('input')); }));
  scrollToLatest();
})();

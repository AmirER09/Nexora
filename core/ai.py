import ipaddress
import socket
from urllib.parse import urlsplit

import requests
from django.conf import settings

def _safe_base_url(base_url, resolve_dns=False):
    try:
        parsed = urlsplit((base_url or "").strip())
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("آدرس API از نظر قالب معتبر نیست.") from exc
    if parsed.scheme not in ("https", "http") or not parsed.hostname:
        raise RuntimeError("آدرس API معتبر نیست؛ آدرس کامل https:// وارد کن.")
    if parsed.username or parsed.password or parsed.fragment or parsed.query:
        raise RuntimeError("آدرس API شامل اطلاعات یا بخش غیرمجاز است.")

    host = parsed.hostname.rstrip(".").lower()
    loopback_names = {"localhost", "127.0.0.1", "::1"}
    is_loopback_name = host in loopback_names or host.endswith(".localhost")
    if is_loopback_name:
        if not settings.DEBUG or parsed.scheme != "http":
            raise RuntimeError("آدرس محلی فقط در حالت توسعه قابل استفاده است.")
        return parsed.geturl().rstrip("/")

    if parsed.scheme != "https":
        raise RuntimeError("برای سرویس‌های بیرونی فقط HTTPS مجاز است.")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and not ip.is_global:
        raise RuntimeError("آدرس‌های IP خصوصی یا داخلی مجاز نیستند.")

    if resolve_dns:
        try:
            records = socket.getaddrinfo(host, port or 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise RuntimeError("دامنه API پیدا نشد؛ آدرس و اتصال اینترنت را بررسی کن.") from exc
        resolved = {ipaddress.ip_address(record[4][0].split("%", 1)[0]) for record in records}
        if not resolved or any(not address.is_global for address in resolved):
            raise RuntimeError("دامنه API به آدرس داخلی یا غیرعمومی اشاره می‌کند و مسدود شد.")

    return parsed.geturl().rstrip("/")

def _response_error(response, api_key):
    message = ""
    try:
        data = response.json()
        error = data.get("error", data)
        if isinstance(error, dict):
            message = str(error.get("message") or error.get("detail") or "")
        elif isinstance(error, str):
            message = error
    except (ValueError, AttributeError):
        message = ""
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    message = " ".join(message.split())[:350]
    if response.status_code in (401, 403):
        return f"احراز هویت API رد شد ({response.status_code})؛ کلید، مدل و دسترسی حساب را بررسی کن."
    if response.status_code == 429:
        return "محدودیت درخواست یا سهمیه سرویس‌دهنده پر شده است (429)."
    if response.status_code >= 500:
        return f"سرویس‌دهنده موقتاً خطا دارد ({response.status_code}). کمی بعد دوباره تلاش کن."
    return f"درخواست API ناموفق بود ({response.status_code})." + (f" جزئیات: {message}" if message else "")

def _post(url, headers, payload, api_key):
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=(5, 45),
            allow_redirects=False,
        )
    except requests.Timeout as exc:
        raise RuntimeError("زمان پاسخ API تمام شد؛ اتصال یا وضعیت سرویس‌دهنده را بررسی کن.") from exc
    except requests.RequestException as exc:
        raise RuntimeError("ارتباط با API برقرار نشد؛ اینترنت، آدرس سرویس و محدودیت شبکه را بررسی کن.") from exc
    if 300 <= response.status_code < 400:
        raise RuntimeError("سرویس‌دهنده درخواست را به آدرس دیگری هدایت کرد؛ برای امنیت، تغییر مسیر دنبال نشد.")
    if not response.ok:
        raise RuntimeError(_response_error(response, api_key))
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("پاسخ سرویس‌دهنده JSON معتبر نبود.") from exc

def _extract_chat_text(data):
    try:
        content = data["choices"][0]["message"].get("content")
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise RuntimeError("ساختار پاسخ API پشتیبانی نمی‌شود؛ مدل و endpoint را بررسی کن.") from exc
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        content = "\n".join(parts)
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("مدل پاسخ متنی برنگرداند؛ شناسه مدل یا تنظیمات آن را بررسی کن.")
    return content.strip()

def call_ai(config, messages):
    api_key = config.get_api_key()
    if not api_key:
        raise RuntimeError("API Key تنظیم نشده یا قابل رمزگشایی نیست. کلید را دوباره در تنظیمات ذخیره کن.")

    system_prompt = (config.system_prompt or "You are Nexora, a practical learning mentor.").strip()
    extra_system = [str(m.get("content", "")) for m in messages if m.get("role") == "system"]
    conversation = [
        {"role": m.get("role"), "content": str(m.get("content", ""))}
        for m in messages
        if m.get("role") in ("user", "assistant")
    ][-16:]
    temperature = max(0.0, min(1.5, float(config.temperature)))
    max_tokens = max(128, min(8192, int(config.max_output_tokens)))

    if config.provider == "gemini":
        model = config.model.removeprefix("models/").strip()
        if not model:
            raise RuntimeError("نام مدل Gemini وارد نشده است.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        system_text = "\n\n".join([system_prompt, *extra_system])
        contents = []
        for message in conversation:
            role = "user" if message["role"] == "user" else "model"
            if message["content"].strip():
                contents.append({"role": role, "parts": [{"text": message["content"]}]})
        data = _post(
            url,
            {"Content-Type": "application/json", "x-goog-api-key": api_key},
            {
                "systemInstruction": {"parts": [{"text": system_text}]},
                "contents": contents,
                "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
            },
            api_key,
        )
        try:
            answer = data["candidates"][0]["content"]["parts"]
            text = "\n".join(part.get("text", "") for part in answer if isinstance(part, dict))
            if text.strip():
                return text.strip()
        except (KeyError, IndexError, TypeError):
            pass
        raise RuntimeError("پاسخ Gemini قابل‌خواندن نبود؛ مدل، سهمیه یا وضعیت ایمنی پاسخ را بررسی کن.")

    if config.provider == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
    else:
        base_url = _safe_base_url(config.base_url, resolve_dns=True)
    if config.provider == "anthropic":
        if base_url.endswith("/v1"):
            url = base_url + "/messages"
        else:
            url = base_url + "/v1/messages"
        system_text = "\n\n".join([system_prompt, *extra_system])
        anthropic_messages = [m for m in conversation if m["content"].strip()]
        data = _post(
            url,
            {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            {
                "model": config.model.strip(),
                "system": system_text,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            api_key,
        )
        if not isinstance(data, dict):
            raise RuntimeError("ساختار پاسخ Claude قابل‌خواندن نبود.")
        blocks = data.get("content", [])
        answer = "\n".join(
            block.get("text", "") for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        )
        if not answer.strip():
            raise RuntimeError("پاسخ Claude متن قابل‌خواندن نداشت.")
        return answer.strip()

    url = base_url if base_url.endswith("/chat/completions") else base_url + "/chat/completions"
    history = [{"role": "system", "content": system_prompt}]
    history.extend({"role": "system", "content": item} for item in extra_system if item)
    history.extend(conversation)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if config.provider == "openrouter" or "openrouter.ai" in base_url.lower():
        headers["HTTP-Referer"] = getattr(settings, "NEXORA_SITE_URL", "http://localhost:8000")
        headers["X-Title"] = "Nexora"
    data = _post(
        url,
        headers,
        {
            "model": config.model.strip(),
            "messages": history,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        api_key,
    )
    return _extract_chat_text(data)

# Nexora

یه وب اپلیکیشن ساخته شده با وایب کدینگ و استفاده از chatgpt free عه که با تمرکز بر روی یادگیری مهارت ها با استفاده از ایجنت های هوش مصنوعیه . شما میتونید کلید api خودتونو داخل برنامه قرار بدید و ازش استفاده کنید.

توجه ! : برخی سرویس های ارائه دهنده api اینترنت ایران رو تحریم کردن در صورت ارور در حین استفاده از مدل ها از vpn  استفاده کنید.
## امکانات

- حساب کاربری و پروفایل شخصی
- مأموریت‌ها، XP و پیشرفت مهارت‌ها
- یادداشت‌ها، ایده‌ها، پروژه‌ها و تخمین زمان
- آزمون محلی و تولید آزمون با AI در صورت تنظیم API
- منتور با زمینه محدود از یادداشت‌ها و پروژه‌های همان کاربر
- اتصال AI به‌ازای هر کاربر، کلید رمزنگاری‌شده و محدودیت درخواست روزانه
- رابط فارسی واکنش‌گرا

## نصب در Windows

به Python 3.11 یا جدیدتر نیاز داری. در پوشه‌ای که `manage.py` قرار دارد، PowerShell را باز کن:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

فایل `.env` را باز کن و `DJANGO_SECRET_KEY` را با خروجی دستور `python -c "import secrets; print(secrets.token_urlsafe(50))"` جایگزین کن. برای اجرای محلی، `DJANGO_DEBUG=True` باقی بماند. سپس:

```powershell
python manage.py migrate
python manage.py check
python manage.py runserver
```

در مرورگر به `http://127.0.0.1:8000` برو.

## اتصال مدل‌ها

در «اتصال ایجنت‌ها» نوع اتصال، مدل و کلید API را وارد کن و «تست اتصال» را اجرا کن. شناسه مدل و API Key باید از پنل رسمی همان سرویس برداشته شوند.

| سرویس | روش اتصال در Nexora | نکته |
|---|---|---|
| OpenRouter | اتصال مستقیم | شناسه مدل باید دقیقاً مطابق فهرست OpenRouter باشد. |
| DeepSeek | OpenAI-compatible | Base URL پیش‌فرض `https://api.deepseek.com` است. |
| Qwen | OpenAI-compatible | Base URL پیش‌فرض بین‌المللی است؛ آدرس منطقه/Workspace حساب تو ممکن است متفاوت باشد. |
| Kimi / Moonshot | OpenAI-compatible | Base URL پیش‌فرض `https://api.moonshot.ai/v1` است. |
| Alibaba Cloud Model Studio | OpenAI-compatible | در صورت نیاز، Base URL منطقه یا Workspace را از پنل خودت وارد کن. |
| OpenAI | OpenAI-compatible | Base URL پیش‌فرض `https://api.openai.com/v1` است. |
| Claude | API رسمی Anthropic | به API Key کنسول Anthropic نیاز دارد؛ ورود یا اشتراک Claude Code به‌تنهایی API Key نیست. |
| Gemini | API اختصاصی Google | مدل و کلید را مطابق تنظیمات فعلی Google AI Studio وارد کن. |
| OpenCode Console | OpenAI-compatible | Base URL پیش‌فرض `https://opencode.ai/inference/openai/v1` است؛ مدل و کلید را از پنل خودت بگیر. بعضی مدل‌های رایگان فقط داخل خود OpenCode در دسترس‌اند. |
| Freebuff و سایر درگاه‌ها | endpoint سفارشی OpenAI-compatible | endpoint رسمی و سازگار با Chat Completions را از پنل سرویس وارد کن؛ Nexora آدرس حدسی نمی‌سازد. |

برای سرویس‌های OpenAI-compatible، Base URL را بدون `/chat/completions` وارد کن؛ Nexora مسیر را اضافه می‌کند. برای APIهای منطقه‌ای، Base URL رسمی حساب خودت را جایگزین کن.

## امنیت

- کلید API در مرورگر نمایش داده نمی‌شود و در دیتابیس با Fernet رمزنگاری می‌شود.
- در توسعه، کلید رمزنگاری از `DJANGO_SECRET_KEY` مشتق می‌شود. برای استقرار عمومی، `NEXORA_ENCRYPTION_KEY` مستقل و ثابت بساز و آن را خارج از Git نگه دار.
- `.env`، دیتابیس، محیط مجازی و فایل‌های کلید را commit نکن.
- درخواست‌های بیرونی فقط از HTTPS استفاده می‌کنند؛ آدرس‌های داخلی و IPهای خصوصی مسدود می‌شوند. در حالت توسعه، localhost برای سرور محلی مجاز است.
- redirectهای API دنبال نمی‌شوند تا کلید ناخواسته به میزبان دیگری فرستاده نشود.
- خطاهای API به‌شکل محدودشده نمایش داده می‌شوند و کلید در پیام خطا برگردانده نمی‌شود.
- قبل از انتشار عمومی، دامنه، HTTPS، `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_SECRET_KEY` و `NEXORA_ENCRYPTION_KEY` را برای محیط خودت تنظیم کن.

برای ساخت کلید Fernet مستقل:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

آن را به‌عنوان `NEXORA_ENCRYPTION_KEY` در `.env` ذخیره کن. این کلید را پیش از ذخیره اولین API Key تعیین کن؛ اگر قبلاً API Key ذخیره کرده‌ای و کلید رمزنگاری را عوض می‌کنی، باید API Key را دوباره وارد کنی. بعد از راه‌اندازی، کلید را گم یا عوض نکن.

## بررسی قبل از انتشار

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

قبل از push، مطمئن شو `.env`، `db.sqlite3`، کلیدهای API و اطلاعات شخصی داخل repository نیستند. برای استقرار عمومی، تنظیمات سرور و سیاست‌های نگهداری/حذف داده را جداگانه بررسی کن.

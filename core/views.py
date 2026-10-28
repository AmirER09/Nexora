import json
import re
import random
from functools import wraps
from django.db.models import F
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from .models import (AIConfig, Mission, ChatMessage, LearningNote, CodeProject, DailyPlan, Quiz, QuizAttempt, AgentNotice, AIUsage, UserProfile)
from .ai import call_ai, _safe_base_url

def onboarding_required(view_func):
    """Require login and the one-time onboarding flow before using the workspace."""
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user, defaults={"display_name": request.user.username}
        )
        if not profile.onboarding_complete:
            return redirect("onboarding")
        return view_func(request, *args, **kwargs)
    return _wrapped

def get_user_ai_config(user):
    return AIConfig.objects.filter(user=user, is_active=True).first()

def ai_quota_available(user, config):
    if not config:
        return False
    return AIUsage.today(user).calls < config.daily_ai_limit

def record_ai_usage(user, prompt_chars=0):
    usage = AIUsage.today(user)
    AIUsage.objects.filter(pk=usage.pk).update(
        calls=F("calls") + 1, estimated_prompt_chars=F("estimated_prompt_chars") + max(0, int(prompt_chars))
    )
    usage.refresh_from_db()
    return usage

INTEREST_CHOICES = [
    ("Python", "Python"), ("Django", "Django و وب"), ("Frontend", "HTML، CSS و JavaScript"),
    ("AI", "هوش مصنوعی"), ("Cybersecurity", "امنیت سایبری"), ("Data", "داده و تحلیل"),
    ("GameDev", "بازی‌سازی"), ("Mobile", "اپلیکیشن موبایل"), ("Problem solving", "حل مسئله و الگوریتم"),
]
THEMES = {"aurora", "ocean", "rose", "emerald", "sunset"}

def signup(request):
    if request.user.is_authenticated:
        return redirect("onboarding" if not getattr(getattr(request.user, "nexora_profile", None), "onboarding_complete", False) else "dashboard")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        UserProfile.objects.create(user=user)
        login(request, user)
        return redirect("onboarding")
    return render(request, "auth/signup.html", {"form": form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect("onboarding" if not getattr(getattr(request.user, "nexora_profile", None), "onboarding_complete", False) else "dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        UserProfile.objects.get_or_create(user=request.user)
        return redirect("onboarding" if not request.user.nexora_profile.onboarding_complete else "dashboard")
    return render(request, "auth/login.html", {"form": form})

def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("login")

@login_required
def onboarding(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user, defaults={"display_name": request.user.username})
    if profile.onboarding_complete:
        return redirect("dashboard")
    if request.method == "POST":
        selected = [x for x in request.POST.getlist("interests") if x in dict(INTEREST_CHOICES)]
        if not selected:
            messages.error(request, "حداقل یک موضوع برای یادگیری انتخاب کن.")
            return render(request, "auth/onboarding.html", {"profile": profile, "choices": INTEREST_CHOICES})
        profile.display_name = (request.POST.get("display_name") or request.user.username).strip()[:80]
        profile.interests = selected
        profile.current_level = request.POST.get("level") if request.POST.get("level") in ("مبتدی", "متوسط", "پیشرفته") else "مبتدی"
        try: profile.daily_minutes = max(10, min(240, int(request.POST.get("daily_minutes", 30))))
        except (TypeError, ValueError): profile.daily_minutes = 30
        profile.main_goal = (request.POST.get("goal") or "ساخت پروژه‌های واقعی")[:240]
        theme = request.POST.get("theme", "aurora")
        profile.theme = theme if theme in THEMES else "aurora"
        profile.onboarding_complete = True
        profile.save()
        
        if not Mission.objects.filter(user=request.user).exists():
            topics = set(selected)
            templates = []
            if "Python" in topics: templates.append({"title":"اولین تابع پایتون", "description":"یک تابع کوچک بنویس، ورودی و خروجی‌اش را آزمایش کن و رفتار ورودی نامعتبر را مشخص کن.", "difficulty":"آسان", "skill":"Python", "xp":30})
            if "Django" in topics: templates.append({"title":"اولین صفحه Django", "description":"یک view و template بساز، URL را وصل کن و مسیر درخواست را توضیح بده.", "difficulty":"آسان", "skill":"Django", "xp":40})
            if "Frontend" in topics: templates.append({"title":"کارت واکنش‌گرا", "description":"با HTML و CSS یک کارت بساز که روی موبایل و دسکتاپ درست نمایش داده شود.", "difficulty":"آسان", "skill":"Frontend", "xp":30})
            if "AI" in topics: templates.append({"title":"مفهوم مدل و داده", "description":"تفاوت دادهٔ ورودی، مدل و خروجی را با یک نمونهٔ کوچک توضیح بده.", "difficulty":"آسان", "skill":"AI basics", "xp":35})
            if "Cybersecurity" in topics: templates.append({"title":"اصول رمز عبور امن", "description":"با یک مثال توضیح بده چرا طول، یکتایی و مدیریت امن رمز عبور مهم‌اند.", "difficulty":"آسان", "skill":"Security", "xp":30})
            if "Data" in topics: templates.append({"title":"تحلیل یک مجموعه داده کوچک", "description":"یک فهرست داده بساز، تعداد، میانگین و بیشترین مقدار را با کد محاسبه کن.", "difficulty":"آسان", "skill":"Data", "xp":35})
            if "GameDev" in topics: templates.append({"title":"منطق یک بازی کوچک", "description":"قوانین یک بازی حدس عدد را بنویس و حالت برد، باخت و تلاش دوباره را پیاده‌سازی کن.", "difficulty":"آسان", "skill":"Game development", "xp":35})
            if "Mobile" in topics: templates.append({"title":"طراحی جریان یک اپ موبایل", "description":"سه صفحه اصلی اپلیکیشن دلخواهت را مشخص کن و مسیر کلیک بین صفحه‌ها را رسم یا توصیف کن.", "difficulty":"آسان", "skill":"Mobile", "xp":25})
            if "Problem solving" in topics: templates.append({"title":"حل مسئله با چند مثال", "description":"یک مسئله ساده انتخاب کن، سه ورودی نمونه بنویس و راه‌حل را قبل از کدنویسی به مراحل کوچک بشکن.", "difficulty":"آسان", "skill":"Problem solving", "xp":30})
            if not templates: templates = DEFAULT_MISSIONS[:2]
            for item in templates[:6]: Mission.objects.create(user=request.user, **item)
        return redirect("dashboard")
    return render(request, "auth/onboarding.html", {"profile": profile, "choices": INTEREST_CHOICES})

@onboarding_required
@require_POST
def update_interests(request):
    """Let a learner extend or adjust topics after the initial onboarding."""
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user, defaults={"display_name": request.user.username}
    )
    known = dict(INTEREST_CHOICES)
    selected = [value for value in request.POST.getlist("interests") if value in known]
    custom_raw = request.POST.get("custom_interests", "")
    custom = []
    for item in re.split(r"[,،;\n]+", custom_raw):
        item = " ".join(item.strip().split())
        if item and len(item) <= 60 and item.casefold() not in {x.casefold() for x in known}:
            custom.append(item)
    merged = []
    seen = set()
    for topic in selected + custom:
        key = topic.casefold()
        if key not in seen:
            merged.append(topic)
            seen.add(key)
        if len(merged) >= 15:
            break
    if not merged:
        messages.error(request, "حداقل یک موضوع برای یادگیری انتخاب یا وارد کن.")
        return redirect("learning_hub")
    profile.interests = merged
    profile.save(update_fields=["interests", "updated_at"])
    AgentNotice.objects.create(
        user=request.user,
        kind="learning_interests_updated",
        title="موضوع‌های یادگیری به‌روزرسانی شد",
        detail="موضوع‌های فعلی: " + ", ".join(merged),
    )
    messages.success(request, "موضوع‌های یادگیری ذخیره شد؛ منتور و مأموریت‌های بعدی از این علایق استفاده می‌کنند.")
    return redirect("learning_hub")

def estimate_project_minutes(title, description="", language="Python"):
    """Estimate project effort without spending API quota; conservative learner-friendly ranges."""
    text = f"{title} {description} {language}".casefold()
    
    if any(word in text for word in ("پرداخت", "payment", "چندفروشنده", "multi-vendor", "real-time", "real time", "مقیاس بزرگ", "production", "استقرار", "deploy", "هوش مصنوعی", " ai ")):
        minutes = 1800
    elif any(word in text for word in ("فروشگاه", "e-commerce", "ecommerce", "سبد خرید", "احراز هویت", "authentication", "api", "داشبورد", "چت", "chat", "بلاگ", "blog", "رزرو", "booking")):
        minutes = 900
    elif any(word in text for word in ("وب‌سایت", "وبسایت", "website", "وب سایت", "crud", "database", "دیتابیس", "مدیریت", "login", "ثبت‌نام", "ثبت نام", "پنل")):
        minutes = 480
    elif any(word in text for word in ("ماشین حساب", "calculator", "todo", "لیست کار", "landing page", "صفحه فرود", "کارت", "تمرین", "اسکریپت", "script")):
        minutes = 120
    else:
        minutes = 240
    desc_len = len(description or "")
    if desc_len > 700:
        minutes += 240
    elif desc_len > 300:
        minutes += 120
    feature_markers = sum((description or "").casefold().count(marker) for marker in ("،", ",", " و ", " همچنین ", "همراه با"))
    minutes += min(feature_markers, 6) * 60
    
    minutes = int(((min(max(minutes, 30), 43200) + 29) // 30) * 30)
    return minutes

@onboarding_required
@require_POST
def save_theme(request):
    if request.method == "POST":
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        theme = request.POST.get("theme", "aurora")
        if theme in THEMES:
            profile.theme = theme
            profile.save(update_fields=["theme", "updated_at"])
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(next_url)
    return redirect("dashboard")

DEFAULT_MISSIONS = [
    {"title": "تابع تخفیف‌ساز", "description": "تابعی در Python بنویس که قیمت و درصد تخفیف را بگیرد و قیمت نهایی را برگرداند. برای ورودی نامعتبر هم یک رفتار مشخص در نظر بگیر.", "difficulty": "آسان", "skill": "Python", "xp": 30},
    {"title": "ردیابی یک باگ", "description": "یک مثال کوچک از خطای TypeError در Python بساز، علتش را توضیح بده و کد را اصلاح کن. هدف، فهمیدن خطاست نه حفظ‌کردن جواب.", "difficulty": "آسان", "skill": "Debugging", "xp": 35},
    {"title": "اولین نمای Django", "description": "یک view ساده بساز که یک صفحه HTML را render کند. مسیر URL را وصل کن و تفاوت view، URL و template را با زبان خودت توضیح بده.", "difficulty": "متوسط", "skill": "Django", "xp": 50},
    {"title": "جست‌وجوی محصولات", "description": "برای فهرست محصولات یک جست‌وجوی ساده پیاده‌سازی کن. ابتدا منطق فیلتر را با یک لیست پایتون آزمایش کن، سپس درباره QuerySet فکر کن.", "difficulty": "متوسط", "skill": "Django", "xp": 60},
]

@onboarding_required
def dashboard(request):
    missions = list(Mission.objects.filter(user=request.user)[:6])
    if not missions:
        for item in DEFAULT_MISSIONS:
            Mission.objects.create(user=request.user, **item)
        missions = list(Mission.objects.filter(user=request.user)[:6])
    completed = Mission.objects.filter(user=request.user, completed=True)
    total_xp = sum(m.xp for m in completed)
    return render(request, "core/dashboard.html", {
        "missions": missions,
        "total_xp": total_xp,
        "completed_count": completed.count(),
        "total_count": Mission.objects.filter(user=request.user).count(),
        "active_mission_count": Mission.objects.filter(user=request.user, completed=False).count(),
        "recent_messages": ChatMessage.objects.filter(user=request.user).order_by("-created_at")[:4],
        "profile": UserProfile.objects.get_or_create(user=request.user, defaults={"display_name": request.user.username})[0],
        "streak": calculate_streak(request),
        "skills": skill_progress(request),
        "latest_notices": AgentNotice.objects.filter(user=request.user)[:3],
    })

@onboarding_required
def mentor(request):
    history = ChatMessage.objects.filter(user=request.user).order_by("created_at")[:60]
    return render(request, "core/mentor.html", {"history": history})

@onboarding_required
def settings_page(request):
    config = get_user_ai_config(request.user)
    if request.method == "POST":
        provider = request.POST.get("provider", "openrouter")
        if provider not in ("openrouter", "openai_compatible", "anthropic", "gemini"):
            provider = "openrouter"
        if config is None:
            config = AIConfig(user=request.user)
        config.name = (request.POST.get("name") or "My AI mentor").strip()[:80]
        config.provider = provider
        preset = request.POST.get("service_preset", "custom")
        presets = {
            "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
            "deepseek": ("https://api.deepseek.com", "deepseek-flash"),
            "qwen": ("https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
            "kimi": ("https://api.moonshot.ai/v1", "kimi-k2.6"),
            "alibaba": ("https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
            "custom": ("", ""),
            "opencode": ("https://opencode.ai/inference/openai/v1", "deepseek-v4.1-flash"),
            "freebuff": ("", ""),
        }
        submitted_model = (request.POST.get("model") or "").strip()[:160]
        submitted_base = (request.POST.get("base_url") or "").strip()
        if provider == "openrouter":
            config.model = submitted_model or "openai/gpt-4o-mini"
            config.base_url = "https://openrouter.ai/api/v1"
        elif provider == "anthropic":
            config.model = submitted_model or "claude-sonnet-4-5"
            config.base_url = submitted_base or "https://api.anthropic.com"
        elif provider == "gemini":
            config.model = submitted_model or "gemini-2.5-flash"
            config.base_url = "https://generativelanguage.googleapis.com"
        else:
            default_base, default_model = presets.get(preset, presets["custom"])
            config.model = submitted_model or default_model
            config.base_url = submitted_base or default_base
            if not config.base_url:
                messages.error(request, "برای OpenCode، Freebuff یا سرویس سفارشی، Base URL سازگار با OpenAI را وارد کن.")
                return redirect("settings")
        if not config.model:
            messages.error(request, "شناسه مدل را وارد کن.")
            return redirect("settings")
        if provider in ("openai_compatible", "anthropic"):
            try:
                config.base_url = _safe_base_url(config.base_url, resolve_dns=False)
            except RuntimeError as exc:
                messages.error(request, str(exc))
                return redirect("settings")
        config.system_prompt = (request.POST.get("system_prompt") or "").strip() or AIConfig._meta.get_field("system_prompt").get_default()
        try:
            config.temperature = max(0.0, min(1.5, float(request.POST.get("temperature", 0.4) or 0.4)))
            config.max_output_tokens = max(128, min(8192, int(request.POST.get("max_output_tokens", 1200) or 1200)))
            config.daily_ai_limit = max(1, min(1000, int(request.POST.get("daily_ai_limit", 40) or 40)))
        except (TypeError, ValueError):
            messages.error(request, "مقادیر محدودیت AI معتبر نیستند.")
            return redirect("settings")
        mode = request.POST.get("mentor_mode", "coach")
        config.mentor_mode = mode if mode in ("coach", "direct", "socratic") else "coach"
        config.auto_notify_agent = request.POST.get("auto_notify_agent") == "on"
        config.is_active = True
        api_key = request.POST.get("api_key", "").strip()
        try:
            if api_key:
                config.set_api_key(api_key)
            elif not config.pk:
                config.encrypted_api_key = ""
            config.save()
            AIConfig.objects.filter(user=request.user).exclude(pk=config.pk).update(is_active=False)
            messages.success(request, "تنظیمات ذخیره شد. کلید API فقط در سرور نگهداری و رمزنگاری می‌شود.")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("settings")
    service_preset = "openai"
    if config and config.provider == "openai_compatible":
        host = (config.base_url or "").lower()
        if "api.deepseek.com" in host:
            service_preset = "deepseek"
        elif "dashscope" in host or "aliyuncs.com" in host:
            service_preset = "alibaba" if "workspace" in host or "maas.aliyuncs.com" in host else "qwen"
        elif "moonshot.ai" in host or "moonshot.cn" in host:
            service_preset = "kimi"
        elif "api.openai.com" in host:
            service_preset = "openai"
        elif "freebuff" in host:
            service_preset = "freebuff"
        elif "opencode.ai/inference" in host:
            service_preset = "opencode"
        elif "localhost" in host or "127.0.0.1" in host:
            service_preset = "custom"
    return render(request, "core/settings.html", {"config": config, "service_preset": service_preset})

@onboarding_required
@require_POST
def test_api(request):
    config = get_user_ai_config(request.user)
    if not config:
        return JsonResponse({"ok": False, "error": "ابتدا تنظیمات API را ذخیره کن."}, status=400)
    if not config.get_api_key():
        return JsonResponse({"ok": False, "error": "برای این حساب هنوز API Key تنظیم نشده."}, status=400)
    if not ai_quota_available(request.user, config):
        return JsonResponse({"ok": False, "error": "سقف درخواست AI امروز این حساب تمام شده."}, status=429)
    try:
        record_ai_usage(request.user, 50)
        reply = call_ai(config, [{"role": "user", "content": "Reply with exactly: Nexora connection works."}])
        return JsonResponse({"ok": True, "reply": reply[:300]})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)[:900]}, status=400)

def execute_chat_action(request, user_text):
    """Execute explicit, allowlisted workspace actions for the signed-in user."""
    text = " ".join((user_text or "").strip().split())
    low = text.casefold()
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user, defaults={"display_name": request.user.username}
    )
    mission_words = ("مأموریت", "ماموریت")
    wants_create = any(w in low for w in mission_words) and any(
        w in low for w in ("بساز", "ایجاد", "اضافه", "جدید", "درست کن", "تعریف کن")
    )
    if wants_create:
        skill_map = {
            "Django": ("Django", "یک قابلیت کوچک Django"),
            "Frontend": ("Frontend", "یک تمرین فرانت‌اند"),
            "AI": ("AI basics", "یک تمرین هوش مصنوعی"),
            "Cybersecurity": ("Security", "یک تمرین امنیتی"),
            "Data": ("Data", "یک تمرین تحلیل داده"),
            "GameDev": ("Game development", "یک تمرین بازی‌سازی"),
            "Mobile": ("Mobile", "یک تمرین اپلیکیشن موبایل"),
            "Problem solving": ("Problem solving", "یک تمرین حل مسئله"),
            "Python": ("Python", "یک تمرین پایتون"),
        }
        chosen = next((x for x in (profile.interests or []) if x in skill_map), "Python")
        skill, default_title = skill_map[chosen]
        subject = re.sub(r"^(?:لطفاً\s*)?(?:یه|یک)?\s*(?:مأموریت|ماموریت)\s*", "", text, flags=re.I)
        subject = re.sub(r"\s*(?:برام|برای من)?\s*(?:بساز|ایجاد کن|اضافه کن|جدید بساز|درست کن|تعریف کن)\s*[.!؟]*$", "", subject, flags=re.I).strip(" :،-")
        subject = re.sub(r"^(?:درباره|برای تمرین|در مورد)\s+", "", subject, flags=re.I).strip()
        generic = subject.casefold() in {"", "جدید", "تازه", "جدید برام", "مناسب سطح من", "برام"}
        if not generic:
            sublow = subject.casefold()
            for token, inferred in (("django", "Django"), ("جنگو", "Django"), ("python", "Python"),
                                    ("پایتون", "Python"), ("html", "Frontend"), ("css", "Frontend"),
                                    ("امنیت", "Cybersecurity"), ("داده", "Data"), ("الگوریتم", "Problem solving")):
                if token in sublow:
                    chosen = inferred
                    skill, default_title = skill_map.get(chosen, (skill, default_title))
                    break
        title = (default_title if generic else subject)[:180]
        if Mission.objects.filter(user=request.user, title=title, completed=False).exists():
            title = f"{title} ({Mission.objects.filter(user=request.user).count() + 1})"
        description = (
            f"هدف: {title}.\n\n"
            f"۱) یک نمونه کوچک و قابل اجرا متناسب با سطح {profile.current_level} بساز.\n"
            "۲) حداقل سه حالت یا ورودی مختلف را آزمایش کن.\n"
            "۳) نتیجه را بررسی کن و توضیح بده چه چیزی یاد گرفتی.\n\n"
            f"معیار تکمیل: خروجی کار می‌کند، آزمایش‌ها ثبت شده‌اند و می‌توانی راه‌حل را توضیح بدهی. "
            f"این تمرین با هدف «{profile.main_goal}» هماهنگ شده است."
        )
        mission = Mission.objects.create(
            user=request.user, title=title, description=description,
            difficulty="آسان" if profile.current_level == "مبتدی" else "متوسط",
            skill=skill, xp=40 if skill == "Django" else 35,
        )
        AgentNotice.objects.create(user=request.user, title=f"مأموریت جدید: {mission.title}", detail=mission.description)
        return f"✅ مأموریت «{mission.title}» ساخته و در داشبورد ذخیره شد.\nمهارت: {mission.skill} · پاداش: {mission.xp} XP\n\n{mission.description}"

    wants_complete = any(w in low for w in ("تکمیل کن", "کامل کن", "انجام شد", "تموم کردم", "تمام کردم", "انجامش دادم")) and any(w in low for w in mission_words)
    if wants_complete:
        candidate = re.sub(r".*?(?:مأموریت|ماموریت)\s*", "", text, count=1, flags=re.I)
        candidate = re.sub(r"\s*(?:رو|را)?\s*(?:تکمیل کن|کامل کن|انجام شد|تموم کردم|تمام کردم|انجامش دادم).*$", "", candidate, flags=re.I).strip(" «»\\\"'،.!؟")
        qs = Mission.objects.filter(user=request.user, completed=False)
        mission = qs.filter(title__icontains=candidate).first() if candidate and candidate not in {"اول", "اولی", "اولین", "رو"} else None
        if mission is None and candidate in {"اول", "اولی", "اولین", "رو", ""}:
            mission = qs.order_by("created_at").first()
        if mission is None:
            return "مأموریت مشخصی پیدا نکردم. اسم دقیقش رو بنویس؛ مثلاً «مأموریت اولین تابع پایتون رو تکمیل کن»."
        mission.completed = True
        mission.completed_at = timezone.now()
        mission.save(update_fields=["completed", "completed_at"])
        total_xp = sum(m.xp for m in Mission.objects.filter(user=request.user, completed=True))
        AgentNotice.objects.create(user=request.user, title=f"مأموریت تکمیل شد: {mission.title}", detail=f"{mission.xp} XP کسب شد.")
        return f"🎉 مأموریت «{mission.title}» تکمیل شد و {mission.xp} XP ثبت شد. مجموع XP تو: {total_xp}."

    if low.startswith(("یادداشت:", "یادداشت ثبت کن:", "یادداشت ذخیره کن:")):
        body = text.split(":", 1)[1].strip()
        parts = [p.strip() for p in body.split("|", 1)]
        if len(parts) != 2 or not all(parts):
            return "برای ثبت یادداشت این قالب رو بفرست:\nیادداشت: عنوان یادداشت | متن یادداشت"
        note = LearningNote.objects.create(user=request.user, title=parts[0][:180], content=parts[1][:12000], topic=(profile.interests or ["عمومی"])[0])
        AgentNotice.objects.create(user=request.user, title=f"یادداشت ثبت شد: {note.title}", detail=note.content[:500])
        return f"📝 یادداشت «{note.title}» ذخیره شد و در بخش یادگیری قابل مشاهده است."

    if low.startswith(("پروژه:", "پروژه ثبت کن:", "پروژه جدید:")):
        body = text.split(":", 1)[1].strip()
        parts = [p.strip() for p in body.split("|")]
        if not parts[0]:
            return "قالب ثبت پروژه: پروژه: نام پروژه | توضیحات | وضعیت (اختیاری)"
        status_text = " ".join(parts[2:]).casefold() if len(parts) > 2 else ""
        status = "done" if any(word in status_text for word in ("تکمیل", "تمام", "done")) else "idea"
        project_description = (parts[1] if len(parts) > 1 else "")[:4000]
        estimated_minutes = estimate_project_minutes(parts[0], project_description, "Python")
        project = CodeProject.objects.create(user=request.user, title=parts[0][:180], description=project_description, language="Python", status=status, estimated_minutes=estimated_minutes)
        AgentNotice.objects.create(user=request.user, title=f"پروژه ثبت شد: {project.title}", detail=f"{project.description} | زمان تخمینی: {project.duration_label}")
        return f"💻 پروژه «{project.title}» در فضای کاری ذخیره شد. زمان تخمینی: {project.duration_label}. وضعیت: {project.get_status_display()}. " + ("در پورتفولیو نمایش داده می‌شود." if status == "done" else "برای نمایش در پورتفولیو، بعداً وضعیتش را تکمیل‌شده کن.")

    wants_project_done = any(word in low for word in ("پروژه", "project")) and any(word in low for word in ("تکمیل کن", "تکمیل‌شده کن", "تمام شد", "تموم شد", "انجام شد"))
    if wants_project_done:
        candidate = re.sub(r".*?(?:پروژه|project)\s*", "", text, count=1, flags=re.I)
        candidate = re.sub(r"\s*(?:رو|را)?\s*(?:تکمیل کن|تکمیل‌شده کن|تمام شد|تموم شد|انجام شد).*$", "", candidate, flags=re.I).strip(" «»\"'،.!؟:")
        projects = CodeProject.objects.filter(user=request.user)
        project = projects.filter(title__icontains=candidate).first() if candidate else None
        if project is None and candidate in ("اول", "اولی", "اولین", "", "رو"):
            project = projects.order_by("created_at").first()
        if project is None:
            return "پروژه‌ای پیدا نکردم. اسم دقیقش رو بنویس؛ مثلاً «پروژه فروشگاه رو تکمیل کن»."
        project.status = "done"
        project.save(update_fields=["status", "updated_at"])
        AgentNotice.objects.create(user=request.user, title=f"پروژه تکمیل شد: {project.title}", detail="این پروژه اکنون در پورتفولیوی کاربر نمایش داده می‌شود.")
        return f"🎉 پروژه «{project.title}» تکمیل‌شده ثبت شد و حالا در پورتفولیو نمایش داده می‌شود."

    
    wants_quiz = any(word in low for word in ("آزمون", "ازمون", "امتحان", "کوییز", "quiz")) and any(
        word in low for word in ("بساز", "ایجاد", "شروع", "بگیر", "جدید", "اضافه", "درست کن", "طراحی کن")
    )
    if wants_quiz:
        topic = detect_quiz_topic(text, profile)
        config = get_user_ai_config(request.user)
        if config and config.get_api_key() and ai_quota_available(request.user, config):
            try:
                quiz = create_ai_quiz(request.user, topic, config=config)
                AgentNotice.objects.create(user=request.user, title=f"آزمون هوش مصنوعی ساخته شد: {quiz.title}", detail=f"{len(quiz.questions)} سؤال درباره {topic}")
                return (f"🧠 آزمون «{quiz.title}» با هوش مصنوعی ساخته و ذخیره شد؛ {len(quiz.questions)} سؤال.\n"
                        f"شروع آزمون: /learning/quizzes/{quiz.pk}/\n"
                        "تصحیح پاسخ‌ها و ذخیره نتیجه روی سرور خود Nexora انجام می‌شود.")
            except Exception as exc:
                quiz = create_local_quiz(request.user, topic)
                AgentNotice.objects.create(user=request.user, title=f"آزمون محلی ساخته شد: {quiz.title}", detail=f"ساخت AI ناموفق بود: {str(exc)[:300]}")
                return (f"⚠️ اتصال/خروجی هوش مصنوعی برای ساخت آزمون موفق نشد؛ برای اینکه معطل نشی یک آزمون محلی ساختم: «{quiz.title}».\n"
                        f"شروع: /learning/quizzes/{quiz.pk}/\n"
                        "این آزمون با AI ساخته نشده؛ تنظیمات API یا مدل را بررسی کن و دوباره امتحان کن.")
        quiz = create_local_quiz(request.user, topic)
        AgentNotice.objects.create(user=request.user, title=f"آزمون محلی ساخته شد: {quiz.title}", detail="برای ساخت آزمون با AI باید API Key تنظیم شده باشد و سقف روزانه باقی مانده باشد.")
        reason = "API تنظیم نشده" if not config or not config.get_api_key() else "سقف درخواست روزانه AI تمام شده"
        return (f"🧠 آزمون محلی «{quiz.title}» ساخته شد. این آزمون با AI تولید نشده چون {reason}.\n"
                f"شروع: /learning/quizzes/{quiz.pk}/\n"
                "برای تولید سؤال با AI، API را در تنظیمات ذخیره کن و دوباره دستور بده.")

    if any(word in low for word in ("پورتفولیو", "نمونه کار", "نمونه‌کار", "portfolio")):
        done_projects = CodeProject.objects.filter(user=request.user, status="done").count()
        done_missions = Mission.objects.filter(user=request.user, completed=True)
        total_xp = sum(item.xp for item in done_missions)
        all_projects = CodeProject.objects.filter(user=request.user).count()
        return (f"📂 وضعیت پورتفولیوت: {done_projects} پروژه تکمیل‌شده از {all_projects} پروژه و "
                f"{done_missions.count()} مأموریت تکمیل‌شده با {total_xp} XP.\n"
                "پورتفولیو از داده‌های واقعی حسابت ساخته می‌شود. برای افزودن پروژه، بنویس: "
                "پروژه: نام پروژه | توضیحات\n"
                "برای نمایش در پورتفولیو، وضعیت آن را در مرکز یادگیری روی «تکمیل‌شده» بگذار.\n"
                "مشاهده پورتفولیو: /portfolio/")

    if any(p in low for p in ("برنامه روزانه بساز", "برنامه امروز بساز", "برنامه یادگیری امروز", "برنامه امروز رو بساز")):
        today = timezone.localdate()
        plan = DailyPlan.objects.filter(user=request.user, plan_date=today).first()
        if plan:
            return "📅 برنامه امروزت از قبل ساخته شده:\n" + "\n".join(f"• {i.get('title', 'تمرین')} ({i.get('minutes', 0)} دقیقه)" for i in plan.items)
        topic = (profile.interests or ["Python"])[0]
        total = max(10, min(240, profile.daily_minutes))
        first, second = max(5, total // 3), max(5, total // 3)
        third = max(5, total - first - second)
        items = [
            {"title": f"مرور {topic}", "minutes": first, "task": f"یک مفهوم از {topic} را با زبان خودت توضیح بده."},
            {"title": "تمرین عملی کوتاه", "minutes": second, "task": f"یک تمرین کوچک مرتبط با {topic} انجام بده."},
            {"title": "ثبت آموخته‌ها", "minutes": third, "task": "یک نکته و یک سؤال برای جلسه بعد ثبت کن."},
        ]
        plan = DailyPlan.objects.create(user=request.user, plan_date=today, title="برنامه یادگیری امروز", items=items, generated_by_ai=False)
        AgentNotice.objects.create(user=request.user, title="برنامه روزانه ساخته شد", detail=plan.title)
        return "📅 برنامه امروز ساخته و ذخیره شد:\n" + "\n".join(f"• {i['title']} ({i['minutes']} دقیقه): {i['task']}" for i in items)
    return None

@onboarding_required
@require_POST
@csrf_protect
def chat_api(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "درخواست نامعتبر است."}, status=400)
    user_text = (payload.get("message") or "").strip()
    if not user_text:
        return JsonResponse({"error": "پیامت خالیه."}, status=400)
    if len(user_text) > 6000:
        return JsonResponse({"error": "پیام خیلی طولانیه؛ کوتاه‌ترش کن."}, status=400)
    ChatMessage.objects.create(user=request.user, role="user", content=user_text)
    
    action_reply = execute_chat_action(request, user_text)
    if action_reply is not None:
        ChatMessage.objects.create(user=request.user, role="assistant", content=action_reply)
        return JsonResponse({"reply": action_reply, "action_executed": True})
    config = get_user_ai_config(request.user)
    if not config or not config.get_api_key():
        answer = "هنوز API تنظیم نشده! از بخش تنظیمات یک ارائه‌دهنده انتخاب کن و API Key را وارد کن. تا آن زمان می‌توانی از مأموریت‌های آماده داشبورد استفاده کنی."
    elif not ai_quota_available(request.user, config):
        answer = "سقف درخواست AI امروز این حساب تمام شده؛ فردا دوباره امتحان کن یا از مأموریت‌ها و ابزارهای آفلاین Nexora استفاده کن."
    else:
        recent = list(ChatMessage.objects.filter(user=request.user).order_by("-created_at")[:16])
        recent.reverse()
        convo = [{"role": m.role, "content": m.content} for m in recent]
        learner = UserProfile.objects.get_or_create(user=request.user, defaults={"display_name": request.user.username})[0]
        interests = ", ".join(learner.interests) or "برنامه‌نویسی عمومی"
        completed_count = Mission.objects.filter(user=request.user, completed=True).count()
        completed_skills = sorted(set(Mission.objects.filter(user=request.user, completed=True).values_list("skill", flat=True)))
        recent_projects = list(CodeProject.objects.filter(user=request.user).order_by("-updated_at")[:6])
        recent_notes = list(LearningNote.objects.filter(user=request.user).order_by("-updated_at")[:8])
        recent_quiz_scores = list(QuizAttempt.objects.filter(quiz__user=request.user).select_related("quiz").order_by("-created_at")[:5])
        project_context = "\n".join(
            f"- [{p.get_status_display()}] {p.title} | زبان: {p.language} | توضیح: {(p.description or 'ندارد')[:450]}"
            for p in recent_projects
        ) or "هنوز ایده یا پروژه‌ای ذخیره نشده"
        note_context = "\n".join(
            f"- یادداشت: {n.title} | موضوع: {n.topic} | متن: {n.content[:800]}"
            for n in recent_notes
        ) or "هنوز یادداشتی ذخیره نشده"
        score_context = ", ".join(
            f"{a.quiz.title}: {a.score}/{a.total}" for a in recent_quiz_scores
        ) or "هنوز آزمونی ثبت نشده"
        convo.insert(0, {"role": "system", "content": (
            f"پروفایل و پیشرفت واقعی یادگیرنده: نام {learner.display_name or request.user.username}؛ "
            f"علایق: {interests}؛ سطح: {learner.current_level}؛ هدف: {learner.main_goal}؛ "
            f"زمان روزانه: {learner.daily_minutes} دقیقه؛ مأموریت‌های تکمیل‌شده: {completed_count}؛ "
            f"مهارت‌های تمرین‌شده: {', '.join(completed_skills) or 'هنوز ثبت نشده'}؛\n"
            f"ایده‌ها و پروژه‌های ذخیره‌شده (دادهٔ خصوصی همین کاربر):\n{project_context}\n"
            f"یادداشت‌های ذخیره‌شده (دادهٔ خصوصی همین کاربر):\n{note_context}\n"
            f"نتایج آزمون‌های اخیر: {score_context}.\n"
            "از این یادداشت‌ها و ایده‌ها هنگام پاسخ‌دادن به پرسش‌های مرتبط استفاده کن؛ اگر کاربر گفت ایده/یادداشتش را بررسی یا خلاصه کن، به همین داده‌های واقعی استناد کن. "
            "اطلاعات این حساب را با هیچ کاربر دیگری ترکیب نکن. اگر داده‌ای در زمینه نیست، صادقانه بگو. "
            "برنامه، مثال‌ها و پیشنهاد پروژه‌ها را بر اساس این داده‌های واقعی و علاقه‌ها تنظیم کن. "
            "پیشرفت یا مهارتی را که در داده‌ها نیست، وانمود نکن. برای موضوعات خارج از علاقه‌ها هم اگر کاربر خواست کمک کن."
        )})
        pending = list(AgentNotice.objects.filter(user=request.user, delivered_to_agent=False)[:10]) if config.auto_notify_agent else []
        if pending:
            notice_text = "رویدادهای جدید Nexora که باید در پاسخ‌های بعدی لحاظ کنی:\n" + "\n".join(f"- {n.title}: {n.detail}" for n in pending)
            convo.insert(0, {"role": "system", "content": notice_text})
        if config.mentor_mode == "direct":
            convo.insert(0, {"role": "system", "content": "حالت پاسخ مستقیم فعال است؛ پاسخ کامل و دقیق بده، اما خطاها و محدودیت‌ها را صادقانه بگو."})
        elif config.mentor_mode == "socratic":
            convo.insert(0, {"role": "system", "content": "حالت سقراطی فعال است؛ با سؤال‌های کوتاه به یادگیرنده کمک کن خودش به پاسخ برسد."})
        else:
            convo.insert(0, {"role": "system", "content": "حالت مربی فعال است؛ اول راهنمایی و سرنخ بده و فقط در صورت نیاز راه‌حل کامل را توضیح بده."})
        try:
            record_ai_usage(request.user, sum(len(m.get("content", "")) for m in convo))
            answer = call_ai(config, convo)
            if pending:
                AgentNotice.objects.filter(user=request.user, pk__in=[n.pk for n in pending]).update(delivered_to_agent=True)
        except Exception as e:
            answer = f"اتصال به هوش مصنوعی ناموفق بود.\n\n{str(e)[:900]}\n\nهزینه‌ای از طرف خود Nexora برای این خطا دریافت نمی‌شود؛ سرویس‌دهنده ممکن است سیاست و سهمیه خودش را داشته باشد."
    ChatMessage.objects.create(user=request.user, role="assistant", content=answer)
    return JsonResponse({"reply": answer})

@onboarding_required
@require_POST
def new_mission(request):
    learner = UserProfile.objects.get_or_create(user=request.user, defaults={"display_name": request.user.username})[0]
    config = get_user_ai_config(request.user)
    if not config or not config.get_api_key() or not ai_quota_available(request.user, config):
        
        fallback_by_interest = {
            "Python": {"title":"تمرین تازه Python", "description":"یک تابع کوچک متناسب با سطح خودت بساز، سه ورودی مختلف را امتحان کن و نتیجه‌ها را توضیح بده.", "difficulty":"آسان", "skill":"Python", "xp":30},
            "Django": {"title":"یک قابلیت کوچک Django", "description":"یک قابلیت ساده به پروژه‌ات اضافه کن؛ URL، view و template مربوط را به هم وصل و آزمایش کن.", "difficulty":"آسان", "skill":"Django", "xp":40},
            "Frontend": {"title":"یک بخش واکنش‌گرا", "description":"یک بخش کوچک با HTML و CSS بساز و نمایش آن را در عرض موبایل و دسکتاپ بررسی کن.", "difficulty":"آسان", "skill":"Frontend", "xp":30},
            "AI": {"title":"آزمایش ورودی و خروجی مدل", "description":"برای یک کاربرد هوش مصنوعی، ورودی، خروجی مورد انتظار و دو حالت خطا را تعریف کن.", "difficulty":"آسان", "skill":"AI basics", "xp":35},
            "Cybersecurity": {"title":"بررسی امنیت یک فرم", "description":"سه ورودی نامعتبر برای یک فرم فرضی مشخص کن و توضیح بده سمت سرور چطور باید اعتبارسنجی شوند.", "difficulty":"آسان", "skill":"Security", "xp":35},
            "Data": {"title":"تحلیل داده کوچک", "description":"یک مجموعه داده کوچک بساز و تعداد، میانگین و بیشترین مقدار را با کد محاسبه کن.", "difficulty":"آسان", "skill":"Data", "xp":35},
            "GameDev": {"title":"قانون تازه برای بازی", "description":"برای یک بازی ساده، یک قانون جدید اضافه کن و حالت‌های برد، باخت و شروع دوباره را آزمایش کن.", "difficulty":"آسان", "skill":"Game development", "xp":35},
            "Mobile": {"title":"جریان صفحه‌های اپ", "description":"سه صفحه برای یک اپ انتخاب کن و مسیر رفت‌وآمد کاربر بین آن‌ها را با یک نمونه ساده مشخص کن.", "difficulty":"آسان", "skill":"Mobile", "xp":25},
            "Problem solving": {"title":"شکستن یک مسئله", "description":"یک مسئله ساده را انتخاب کن، سه ورودی نمونه بنویس و راه‌حل را به گام‌های کوچک تقسیم کن.", "difficulty":"آسان", "skill":"Problem solving", "xp":30},
        }
        interest = next((topic for topic in learner.interests if topic in fallback_by_interest), "Python")
        item = fallback_by_interest[interest].copy()
        item["title"] = f"{item['title']} · {Mission.objects.filter(user=request.user).count() + 1}"
        mission = Mission.objects.create(user=request.user, **item)
        AgentNotice.objects.create(user=request.user, title=f"مأموریت جدید: {mission.title}", detail=f"مهارت: {mission.skill}. دشواری: {mission.difficulty}. هدف: {mission.description}")
        return JsonResponse({"ok": True, "id": mission.id, "title": mission.title, "description": mission.description,
                             "skill": mission.skill, "difficulty": mission.difficulty, "xp": mission.xp,
                             "notice": "مأموریت ذخیره شد؛ رویداد آن برای منتور ثبت شد.",
                             "total_count": Mission.objects.filter(user=request.user).count()})
    interest_text = ", ".join(learner.interests) or "Python"
    prompt = (
        "Create exactly one beginner-friendly, practical programming learning mission in Persian. "
        "Return only JSON with keys title, description, difficulty, skill, xp. "
        "The task must be achievable in 20-45 minutes, include clear acceptance criteria, and teach one concept. "
        f"Match the learner's interests ({interest_text}), level ({learner.current_level}) and goal ({learner.main_goal}). "
        "Avoid repeating generic calculator or todo tasks. Current mission titles: " +
        ", ".join(Mission.objects.filter(user=request.user).values_list("title", flat=True)[:20])
    )
    try:
        record_ai_usage(request.user, len(prompt))
        text = call_ai(config, [{"role": "user", "content": prompt}])
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start:end+1])
        mission = Mission.objects.create(
            user=request.user, title=str(data.get("title", "مأموریت تازه"))[:180],
            description=str(data.get("description", ""))[:5000],
            difficulty=str(data.get("difficulty", "شروع"))[:24],
            skill=str(data.get("skill", "Python"))[:80],
            xp=max(10, min(150, int(data.get("xp", 30)))),
        )
        AgentNotice.objects.create(user=request.user, title=f"مأموریت جدید: {mission.title}", detail=f"مهارت: {mission.skill}. دشواری: {mission.difficulty}. هدف: {mission.description}")
        return JsonResponse({"ok": True, "id": mission.id, "title": mission.title, "description": mission.description,
                             "skill": mission.skill, "difficulty": mission.difficulty, "xp": mission.xp,
                             "notice": "مأموریت ذخیره شد؛ رویداد آن برای منتور ثبت شد.",
                             "total_count": Mission.objects.filter(user=request.user).count()})
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"ساخت مأموریت ممکن نشد: {str(e)[:500]}"}, status=400)

@onboarding_required
@require_POST
def auto_mission(request):
    """Let Nexora proactively create the next mission after onboarding/progress.

    This is intentionally AI-only: if AI is not configured or quota is exhausted,
    no fake AI-created mission is stored. The user can still use the manual local
    fallback button when desired.
    """
    active_count = Mission.objects.filter(user=request.user, completed=False).count()
    if active_count >= 6:
        return JsonResponse({"ok": True, "created": False, "reason": "enough_active_missions"})
    
    from datetime import timedelta
    recent_auto = AgentNotice.objects.filter(
        user=request.user, kind="auto_mission_generated", created_at__gte=timezone.now() - timedelta(minutes=30)
    ).exists()
    if recent_auto:
        return JsonResponse({"ok": True, "created": False, "reason": "cooldown"})

    config = get_user_ai_config(request.user)
    if not config or not config.get_api_key() or not ai_quota_available(request.user, config):
        return JsonResponse({"ok": True, "created": False, "reason": "ai_unavailable"})

    profile = UserProfile.objects.get_or_create(
        user=request.user, defaults={"display_name": request.user.username}
    )[0]
    active_titles = list(Mission.objects.filter(user=request.user, completed=False).values_list("title", flat=True)[:12])
    completed_titles = list(Mission.objects.filter(user=request.user, completed=True).values_list("title", flat=True)[:12])
    interests = ", ".join(profile.interests or ["Python"])
    prompt = (
        "You are Nexora's autonomous learning planner. Create exactly one next learning mission now; "
        "do not ask the learner to request it. Return ONLY valid JSON with keys title, description, difficulty, skill, xp. "
        "Write in Persian. Make it specific, practical, achievable in 20-45 minutes, with clear acceptance criteria. "
        "Adapt to level and goal, build on completed work, and avoid duplicating active missions. XP must be 10-100. "
        f"Learner interests: {interests}. Level: {profile.current_level}. Goal: {profile.main_goal}. "
        f"Daily minutes: {profile.daily_minutes}. Active missions to avoid: {active_titles}. "
        f"Completed missions to build on: {completed_titles}."
    )
    try:
        record_ai_usage(request.user, len(prompt))
        raw = call_ai(config, [{"role": "user", "content": prompt}])
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("پاسخ AI ساختار JSON نداشت")
        data = json.loads(raw[start:end + 1])
        title = str(data.get("title", "مأموریت بعدی Nexora")).strip()[:180]
        description = str(data.get("description", "")).strip()[:5000]
        if not title or not description:
            raise ValueError("عنوان یا توضیح مأموریت خالی بود")
        with transaction.atomic():
            
            if Mission.objects.filter(user=request.user, title=title, completed=False).exists():
                return JsonResponse({"ok": True, "created": False, "reason": "duplicate"})
            mission = Mission.objects.create(
                user=request.user, title=title, description=description,
                difficulty=str(data.get("difficulty", "آسان"))[:24],
                skill=str(data.get("skill", interests.split(",")[0]))[:80],
                xp=max(10, min(100, int(data.get("xp", 30)))),
            )
            AgentNotice.objects.create(
                user=request.user, kind="auto_mission_generated",
                title=f"منتور مأموریت بعدی را ساخت: {mission.title}", detail=mission.description,
            )
        return JsonResponse({
            "ok": True, "created": True, "id": mission.id, "title": mission.title,
            "description": mission.description, "skill": mission.skill,
            "difficulty": mission.difficulty, "xp": mission.xp,
            "total_count": Mission.objects.filter(user=request.user).count(),
            "active_count": Mission.objects.filter(user=request.user, completed=False).count(),
        })
    except Exception as exc:
        return JsonResponse({"ok": False, "created": False, "error": f"ساخت خودکار مأموریت ناموفق بود: {str(exc)[:350]}"}, status=502)

@onboarding_required
@require_POST
def delete_mission(request, mission_id):
    mission = Mission.objects.filter(pk=mission_id, user=request.user).first()
    if mission is None:
        return JsonResponse({"ok": False, "error": "مأموریت پیدا نشد یا متعلق به این حساب نیست."}, status=404)
    title = mission.title
    mission.delete()
    AgentNotice.objects.create(user=request.user, kind="mission_deleted", title=f"مأموریت حذف شد: {title}", detail="کاربر این مأموریت را از داشبورد حذف کرد.")
    return JsonResponse({
        "ok": True,
        "total_count": Mission.objects.filter(user=request.user).count(),
        "completed_count": Mission.objects.filter(user=request.user, completed=True).count(),
        "active_count": Mission.objects.filter(user=request.user, completed=False).count(),
        "xp": sum(m.xp for m in Mission.objects.filter(user=request.user, completed=True)),
    })

@onboarding_required
@require_POST
def complete_mission(request):
    try:
        data = json.loads(request.body or "{}")
        mission = Mission.objects.get(pk=int(data.get("id")), user=request.user)
    except (json.JSONDecodeError, ValueError, Mission.DoesNotExist, TypeError):
        return JsonResponse({"ok": False, "error": "مأموریت پیدا نشد."}, status=404)
    if not mission.completed:
        mission.completed = True
        mission.completed_at = timezone.now()
        mission.save(update_fields=["completed", "completed_at"])
    return JsonResponse({"ok": True, "xp": sum(m.xp for m in Mission.objects.filter(user=request.user, completed=True)),
                         "completed_count": Mission.objects.filter(user=request.user, completed=True).count(),
                         "total_count": Mission.objects.filter(user=request.user).count()})

def calculate_streak(request):
    dates = set(Mission.objects.filter(user=request.user, completed=True, completed_at__isnull=False).values_list("completed_at__date", flat=True))
    from datetime import timedelta
    today = timezone.localdate()
    cursor = today if today in dates else today - timedelta(days=1)
    count = 0
    while cursor in dates:
        count += 1
        cursor -= timedelta(days=1)
    return count

def skill_progress(request):
    rows = {}
    for mission in Mission.objects.filter(user=request.user, completed=True):
        rows[mission.skill] = rows.get(mission.skill, 0) + mission.xp
    return [{"name": name, "xp": xp, "level": xp // 100 + 1, "progress": xp % 100} for name, xp in sorted(rows.items(), key=lambda x: -x[1])]

@onboarding_required
def learning_hub(request):
    profile = UserProfile.objects.get_or_create(user=request.user, defaults={"display_name": request.user.username})[0]
    today = timezone.localdate()
    plan = DailyPlan.objects.filter(user=request.user, plan_date=today).first()
    return render(request, "core/learning_hub.html", {
        "profile": profile, "plan": plan, "notes": LearningNote.objects.filter(user=request.user)[:8],
        "projects": CodeProject.objects.filter(user=request.user)[:8], "quizzes": Quiz.objects.filter(user=request.user)[:8],
        "interest_choices": INTEREST_CHOICES,
        "custom_interests": [topic for topic in (profile.interests or []) if topic not in dict(INTEREST_CHOICES)],
        "skills": skill_progress(request), "streak": calculate_streak(request),
        "usage": AIUsage.today(request.user), "notices": AgentNotice.objects.filter(user=request.user)[:8],
        "recent_quiz_attempts": QuizAttempt.objects.filter(quiz__user=request.user).select_related("quiz").order_by("-created_at")[:5],
    })

@onboarding_required
@require_POST
def generate_daily_plan(request):
    
    today = timezone.localdate()
    existing = DailyPlan.objects.filter(user=request.user, plan_date=today).first()
    if existing:
        return JsonResponse({"ok": True, "title": existing.title, "items": existing.items, "cached": True})
    profile = UserProfile.objects.get_or_create(user=request.user, defaults={"display_name": request.user.username})[0]
    topic = (profile.interests or ["Python"])[0]
    total = max(10, profile.daily_minutes)
    first = max(5, total // 3)
    second = max(5, total // 3)
    third = max(5, total - first - second)
    items = [
        {"title": f"مرور {topic}", "minutes": first, "reason": "یادآوری فعال", "task": f"یک مفهوم از {topic} را بدون نگاه‌کردن به منبع، با زبان خودت توضیح بده."},
        {"title": "تمرین عملی کوتاه", "minutes": second, "reason": "یادگیری با ساختن", "task": f"یک تمرین کوچک مرتبط با {topic} انجام بده و نتیجه را آزمایش کن."},
        {"title": "ثبت آموخته‌ها", "minutes": third, "reason": "ماندگاری بیشتر", "task": "یک نکته‌ای که یاد گرفتی و یک سؤال برای جلسه بعد در دفتر یادداشت ثبت کن."},
    ]
    plan = DailyPlan.objects.create(user=request.user, plan_date=today, title="برنامه یادگیری امروز", items=items, generated_by_ai=False)
    AgentNotice.objects.create(user=request.user, title="برنامه روزانه ساخته شد", detail=f"{plan.title}: " + "; ".join(str(i.get("title", "")) for i in items))
    return JsonResponse({"ok": True, "title": plan.title, "items": plan.items, "generated_by_ai": False})

@onboarding_required
@require_POST
def save_note(request):
    title = (request.POST.get("title") or "").strip()
    content = (request.POST.get("content") or "").strip()
    if not title or not content:
        messages.error(request, "عنوان و متن یادداشت را وارد کن.")
    else:
        LearningNote.objects.create(user=request.user, title=title[:180], content=content[:12000], topic=(request.POST.get("topic") or "عمومی")[:80])
        messages.success(request, "یادداشت ذخیره شد.")
    return redirect("learning_hub")

@onboarding_required
@require_POST
def delete_note(request, note_id):
    note = LearningNote.objects.filter(pk=note_id, user=request.user).first()
    if note is None:
        messages.error(request, "یادداشت پیدا نشد یا به این حساب تعلق ندارد.")
    else:
        note.delete()
        messages.success(request, "یادداشت حذف شد.")
    return redirect("learning_hub")

@onboarding_required
@require_POST
def save_project(request):
    title = (request.POST.get("title") or "").strip()
    description = (request.POST.get("description") or "").strip()[:4000]
    language = (request.POST.get("language") or "Python").strip()[:60] or "Python"
    if not title:
        messages.error(request, "نام پروژه اجباری است.")
    else:
        raw_minutes = (request.POST.get("estimated_minutes") or "auto").strip().casefold()
        if raw_minutes in ("", "auto", "خودکار"):
            estimated_minutes = estimate_project_minutes(title, description, language)
        else:
            try:
                estimated_minutes = max(30, min(43200, int(raw_minutes)))
                estimated_minutes = int(((estimated_minutes + 29) // 30) * 30)
            except (TypeError, ValueError):
                estimated_minutes = estimate_project_minutes(title, description, language)
        project = CodeProject.objects.create(
            user=request.user, title=title[:180], description=description,
            language=language, code=(request.POST.get("code") or "")[:30000],
            status=request.POST.get("status") if request.POST.get("status") in ("idea", "active", "done") else "idea",
            estimated_minutes=estimated_minutes,
        )
        messages.success(request, f"پروژه ذخیره شد؛ زمان تقریبی: {project.duration_label}. این تخمین را می‌توانی در فرم پروژه تغییر بدهی.")
    return redirect("learning_hub")

@onboarding_required
@require_POST
def delete_project(request, project_id):
    project = CodeProject.objects.filter(pk=project_id, user=request.user).first()
    if project is None:
        messages.error(request, "پروژه پیدا نشد یا به این حساب تعلق ندارد.")
    else:
        project.delete()
        messages.success(request, "پروژه حذف شد.")
    return redirect("learning_hub")

def quiz_question_bank(topic):
    """Curated local question bank. Each item has four options and one correct answer."""
    key = (topic or "Python").casefold()
    if "django" in key or "جنگو" in key:
        raw = [
            ("در Django مسئول رسیدگی به درخواست و آماده‌کردن پاسخ چیست؟", ["View", "Migration", "Static file", "Model field"], 0, "View منطق رسیدگی به درخواست را اجرا می‌کند."),
            ("برای نمایش HTML با داده‌های پویا از چه چیزی استفاده می‌شود؟", ["Template", "requirements.txt", "venv", "SQL console"], 0, "Template خروجی HTML را با context رندر می‌کند."),
            ("برای تعریف مسیر URL معمولاً از چه چیزی استفاده می‌کنیم؟", ["path()", "makemigrations()", "print()", "collectstatic()"], 0, "تابع path مسیر را به view متصل می‌کند."),
            ("کدام دستور تغییرات مدل را به فایل migration تبدیل می‌کند؟", ["makemigrations", "migrate فقط", "runserver", "createsuperuser"], 0, "makemigrations فایل migration تولید می‌کند."),
            ("ForeignKey معمولاً چه رابطه‌ای می‌سازد؟", ["چندبه‌یک", "چندبه‌چند", "فقط یک‌به‌یک", "بدون رابطه"], 0, "ForeignKey معمولاً رابطه چند رکورد به یک رکورد را مدل می‌کند."),
            ("برای گرفتن یک شیء و نمایش خطای 404 در صورت نبودن، کدام میانبر کاربردی است؟", ["get_object_or_404", "redirect_only", "admin.site", "JsonResponse فقط"], 0, "get_object_or_404 در صورت نبودن شیء پاسخ 404 می‌دهد."),
        ]
    elif any(x in key for x in ("html", "css", "frontend", "فرانت")):
        raw = [
            ("HTML بیشتر برای چه کاری استفاده می‌شود؟", ["ساختار محتوا", "ذخیره دیتابیس", "اجرای migration", "مدیریت رمز"], 0, "HTML ساختار محتوا را مشخص می‌کند."),
            ("کدام ویژگی CSS فاصله داخلی عنصر را تنظیم می‌کند؟", ["padding", "href", "def", "SELECT"], 0, "padding فاصله بین محتوا و لبه داخلی است."),
            ("کدام گزینه برای چیدمان واکنش‌گرا کاربرد دارد؟", ["Flexbox یا Grid", "print()", "ForeignKey", "pip"], 0, "Flexbox و Grid ابزارهای چیدمان هستند."),
            ("برای لینک‌دادن در HTML معمولاً از کدام تگ استفاده می‌شود؟", ["a", "div فقط", "meta", "script فقط"], 0, "تگ a پیوند ایجاد می‌کند."),
            ("کدام واحد CSS نسبت به اندازه فونت عنصر محاسبه می‌شود؟", ["em", "px همیشه", "kg", "ms"], 0, "em بر پایه اندازه فونت عنصر محاسبه می‌شود."),
            ("برای انتخاب عنصر با شناسه در CSS از چه نمادی استفاده می‌شود؟", ["#", ".", "@", "$"], 0, "# برای انتخاب id به‌کار می‌رود."),
        ]
    elif any(x in key for x in ("امنیت", "cyber", "سایبری")):
        raw = [
            ("کدام روش برای ذخیره رمز عبور کاربران مناسب‌تر است؟", ["هش امن با salt", "متن ساده", "Base64", "فایل عمومی"], 0, "رمز باید با الگوریتم هش مناسب و salt ذخیره شود."),
            ("اعتبارسنجی مهم ورودی کاربر بهتر است کجا انجام شود؟", ["سمت سرور", "فقط در CSS", "فقط در مرورگر", "در نام فایل"], 0, "اعتبارسنجی سمت سرور قابل دور زدن از مرورگر نیست."),
            ("CSRF بیشتر برای جلوگیری از چه چیزی است؟", ["درخواست ناخواسته از طرف مرورگر کاربر", "حذف باگ نحوی", "کندی CPU", "فشرده‌سازی تصویر"], 0, "CSRF از برخی درخواست‌های جعلی با اعتبار کاربر جلوگیری می‌کند."),
            ("کدام کار برای API Key امن‌تر است؟", ["نگهداری سمت سرور", "قرار دادن در JavaScript عمومی", "ارسال در URL", "انتشار در Git"], 0, "کلید محرمانه نباید به مرورگر یا مخزن عمومی برسد."),
            ("HTTPS چه چیزی را فراهم می‌کند؟", ["رمزنگاری ارتباط در مسیر", "تضمین نبود همه باگ‌ها", "افزایش RAM", "جلوگیری از هرزنامه"], 0, "HTTPS ارتباط میان مرورگر و سرور را رمزنگاری می‌کند."),
        ]
    elif any(x in key for x in ("هوش مصنوعی", " ai ", "ai basics")):
        raw = [
            ("در یک درخواست مدل زبانی، prompt چیست؟", ["دستور و زمینه ورودی", "کارت گرافیک", "فایل دیتابیس", "رمز عبور"], 0, "Prompt دستور و زمینه‌ای است که به مدل داده می‌شود."),
            ("چرا خروجی مدل باید بررسی شود؟", ["ممکن است اشتباه یا ساختگی باشد", "همیشه ثابت است", "هیچ‌وقت متن نیست", "چون فقط تصویر می‌سازد"], 0, "خروجی مدل می‌تواند خطا داشته باشد و نیازمند ارزیابی است."),
            ("API Key را کجا نگه داریم؟", ["سمت سرور و محرمانه", "در HTML عمومی", "داخل URL", "در پیام خطا"], 0, "کلید API باید محرمانه بماند."),
            ("temperature معمولاً چه چیزی را تغییر می‌دهد؟", ["میزان تنوع خروجی", "اندازه دیتابیس", "وضوح نمایشگر", "سرعت اینترنت"], 0, "temperature بالاتر معمولاً تنوع پاسخ را بیشتر می‌کند."),
            ("برای کاهش هزینه API کدام روش مناسب است؟", ["درخواست فقط هنگام نیاز و محدودیت مصرف", "ارسال کل تاریخچه همیشه", "تکرار درخواست در حلقه", "خاموش‌کردن اعتبارسنجی"], 0, "محدودکردن درخواست و زمینه، مصرف را کاهش می‌دهد."),
        ]
    elif any(x in key for x in ("داده", "data")):
        raw = [
            ("میانگین حسابی چگونه به‌دست می‌آید؟", ["مجموع تقسیم بر تعداد", "بزرگ‌ترین منهای کوچک‌ترین", "تعداد تقسیم بر مجموع", "فقط مرتب‌سازی"], 0, "میانگین برابر مجموع مقادیر تقسیم بر تعداد آن‌هاست."),
            ("در Python کدام ساختار برای نگهداری زوج کلید-مقدار مناسب است؟", ["dict", "int", "bool", "None"], 0, "dict داده را به شکل کلید و مقدار نگه می‌دارد."),
            ("برای شمارش تعداد اعضای یک لیست از چه چیزی استفاده می‌شود؟", ["len()", "sum() همیشه", "max()", "type()"], 0, "len تعداد اعضا را برمی‌گرداند."),
            ("میانه (median) در داده‌های مرتب چه مفهومی دارد؟", ["مقدار میانی", "مجموع همه مقادیر", "بزرگ‌ترین مقدار", "تعداد ستون‌ها"], 0, "میانه مقدار وسط داده‌های مرتب است."),
            ("چرا داده‌ها را پیش از تحلیل پاک‌سازی می‌کنند؟", ["برای رسیدگی به داده ناقص یا ناسازگار", "برای تغییر تصادفی جواب", "برای حذف همه داده‌ها", "برای رمزگذاری CSS"], 0, "پاک‌سازی کیفیت و سازگاری داده را بهتر می‌کند."),
        ]
    elif any(x in key for x in ("الگوریتم", "حل مسئله", "problem")):
        raw = [
            ("اولین قدم خوب برای حل مسئله برنامه‌نویسی چیست؟", ["تعریف دقیق مسئله و ورودی/خروجی", "نوشتن کد تصادفی", "حذف تست‌ها", "انتخاب رنگ رابط"], 0, "باید مسئله و ورودی/خروجی روشن باشند."),
            ("چرا از چند مورد آزمایشی استفاده می‌کنیم؟", ["برای پوشش حالت‌های مختلف", "برای کندکردن برنامه", "برای جایگزینی کد", "برای حذف ورودی"], 0, "چند تست می‌توانند خطاهای حالت‌های مرزی را آشکار کنند."),
            ("پیچیدگی زمانی الگوریتم درباره چیست؟", ["رشد زمان اجرا با اندازه ورودی", "رنگ خروجی", "حجم مانیتور", "نام متغیر"], 0, "پیچیدگی زمانی رشد هزینه اجرا را توصیف می‌کند."),
            ("کدام ساختار برای تکرار روی اعضای یک لیست مناسب است؟", ["for", "class فقط", "import فقط", "return فقط"], 0, "for برای پیمایش اعضای مجموعه کاربرد دارد."),
            ("حالت مرزی (edge case) چیست؟", ["ورودی یا وضعیت خاصی که ممکن است مشکل ایجاد کند", "فقط حالت عادی", "نام فایل", "نوع فونت"], 0, "حالت‌های مرزی رفتار برنامه را در شرایط خاص می‌سنجند."),
        ]
    else:
        raw = [
            ("کدام نوع داده برای نگهداری چند مقدار مرتب مناسب است؟", ["list", "int", "bool", "None"], 0, "list مجموعه‌ای مرتب و قابل تغییر است."),
            ("در Python برای تعریف تابع از چه کلمه‌ای استفاده می‌شود؟", ["func", "def", "function", "make"], 1, "تعریف تابع با def آغاز می‌شود."),
            ("کدام عبارت مقدار بولی True را نشان می‌دهد؟", ["'True'", "1 == 2", "True", "None"], 2, "True مقدار بولی است؛ 'True' یک رشته است."),
            ("برای تبدیل رشته عددی '12' به عدد صحیح از چه چیزی استفاده می‌شود؟", ["int('12')", "str(12)", "list(12)", "bool('12') فقط"], 0, "int رشته عددی را به عدد صحیح تبدیل می‌کند."),
            ("کدام ساختار برای اجرای شرط استفاده می‌شود؟", ["if", "for فقط", "import", "class"], 0, "if بر اساس یک شرط مسیر اجرا را انتخاب می‌کند."),
            ("در Python کدام علامت برای مقایسه برابری است؟", ["==", "=", "!= فقط", ":="], 0, "== دو مقدار را از نظر برابری مقایسه می‌کند."),
        ]
    questions = []
    for question, options, answer_index, explanation in random.sample(raw, k=min(5, len(raw))):
        
        pairs = list(enumerate(options))
        random.shuffle(pairs)
        new_options = [option for _, option in pairs]
        new_answer = next(i for i, (original_i, _) in enumerate(pairs) if original_i == answer_index)
        questions.append({"question": question, "options": new_options, "answer_index": new_answer, "explanation": explanation})
    return questions

def detect_quiz_topic(text, profile=None):
    low = (text or "").casefold()
    choices = [
        (("django", "جنگو"), "Django"), (("html", "css", "فرانت", "javascript", "جاوااسکریپت"), "Frontend"),
        (("امنیت", "سایبری", "cybersecurity"), "Cybersecurity"), (("هوش مصنوعی", " artificial intelligence ", " ai "), "AI"),
        (("داده", "تحلیل داده", "data"), "Data"), (("الگوریتم", "حل مسئله", "algorithm"), "Problem solving"),
        (("پایتون", "python"), "Python"),
    ]
    for tokens, topic in choices:
        if any(token in low for token in tokens):
            return topic
    interests = getattr(profile, "interests", []) or []
    map_topics = {"Django": "Django", "Frontend": "Frontend", "Cybersecurity": "Cybersecurity", "AI": "AI", "Data": "Data", "Problem solving": "Problem solving", "Python": "Python"}
    return next((map_topics[item] for item in interests if item in map_topics), "Python")

def create_ai_quiz(user, topic, config=None):
    """Generate a validated quiz with the user's configured AI; scoring remains local."""
    config = config or get_user_ai_config(user)
    if not config or not config.get_api_key():
        raise RuntimeError("API Key برای این حساب تنظیم نشده است.")
    if not ai_quota_available(user, config):
        raise RuntimeError("سقف درخواست روزانه AI تمام شده است.")
    profile = UserProfile.objects.filter(user=user).first()
    level = profile.current_level if profile else "مبتدی"
    prompt = (
        "یک آزمون آموزشی دقیق به زبان فارسی تولید کن. فقط JSON معتبر و بدون Markdown برگردان. "
        "ساختار JSON دقیقاً شامل title و questions باشد. questions باید دقیقاً 5 عضو داشته باشد. "
        "هر سؤال: question (رشته)، options (آرایه دقیقاً 4 رشته)، answer_index (عدد صحیح 0 تا 3)، explanation (رشته کوتاه فارسی). "
        "پاسخ صحیح باید با answer_index دقیقاً به یکی از گزینه‌ها اشاره کند. گزینه‌ها نباید تکراری باشند. "
        "از سؤال‌های مبهم یا چندجوابی دوری کن؛ توضیح پاسخ را آموزشی بنویس. "
        f"موضوع آزمون: {topic}. سطح یادگیرنده: {level}. عنوان و سؤال‌ها فارسی باشند، نام مفاهیم فنی می‌تواند انگلیسی بماند."
    )
    record_ai_usage(user, len(prompt))
    response_text = call_ai(config, [{"role": "user", "content": prompt}])
    
    start, end = response_text.find("{"), response_text.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("مدل خروجی JSON معتبر برای آزمون برنگرداند.")
    try:
        data = json.loads(response_text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise RuntimeError("ساختار JSON آزمون از مدل قابل‌خواندن نبود.") from exc
    raw_questions = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(raw_questions, list) or len(raw_questions) < 5:
        raise RuntimeError("مدل کمتر از ۵ سؤال معتبر تولید کرد.")
    validated = []
    for item in raw_questions[:5]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()[:1200]
        options = item.get("options")
        explanation = str(item.get("explanation", "")).strip()[:2000]
        try:
            answer_index = int(item.get("answer_index", -1))
        except (TypeError, ValueError):
            answer_index = -1
        if not question or not isinstance(options, list) or len(options) != 4 or not 0 <= answer_index < 4:
            continue
        options = [str(option).strip()[:500] for option in options]
        if any(not option for option in options) or len(set(options)) != 4:
            continue
        validated.append({"question": question, "options": options, "answer_index": answer_index, "explanation": explanation})
    if len(validated) != 5:
        raise RuntimeError("سؤال‌های تولیدشده اعتبارسنجی نشدند؛ دوباره امتحان کن.")
    title = str(data.get("title") or f"آزمون هوش مصنوعی {topic}").strip()[:180]
    return Quiz.objects.create(user=user, title=title, topic=topic, questions=validated, generated_by_ai=True)

def create_local_quiz(user, topic):
    topic = (topic or "Python").strip()[:100] or "Python"
    questions = quiz_question_bank(topic)
    return Quiz.objects.create(user=user, title=f"آزمون محلی {topic}", topic=topic, questions=questions, generated_by_ai=False)

@onboarding_required
@require_POST
def generate_quiz(request):
    topic = (request.POST.get("topic") or "Python").strip()[:100] or "Python"
    config = get_user_ai_config(request.user)
    if config and config.get_api_key() and ai_quota_available(request.user, config):
        try:
            quiz = create_ai_quiz(request.user, topic, config=config)
            AgentNotice.objects.create(user=request.user, title=f"آزمون AI ساخته شد: {quiz.title}", detail=f"{len(quiz.questions)} سؤال درباره {topic}")
            messages.success(request, f"آزمون «{quiz.title}» با هوش مصنوعی ساخته شد.")
        except Exception as exc:
            quiz = create_local_quiz(request.user, topic)
            messages.warning(request, f"ساخت آزمون با AI ناموفق بود؛ نسخه محلی ساخته شد. علت: {str(exc)[:180]}")
    else:
        quiz = create_local_quiz(request.user, topic)
        reason = "API تنظیم نشده" if not config or not config.get_api_key() else "سقف روزانه AI تمام شده"
        messages.warning(request, f"آزمون محلی ساخته شد، نه AI؛ {reason}.")
    return redirect("quiz_detail", quiz_id=quiz.pk)

@onboarding_required
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id, user=request.user)
    public_questions = [{"question": q.get("question", "سؤال"), "options": q.get("options", []), "number": i + 1} for i, q in enumerate(quiz.questions) if q.get("options")]
    return render(request, "core/quiz_detail.html", {"quiz": quiz, "public_questions": public_questions})

@onboarding_required
@require_POST
def submit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id, user=request.user)
    answers = {}
    score = 0
    for i, q in enumerate(quiz.questions):
        try:
            chosen = int(request.POST.get(f"q_{i}", "-1"))
        except ValueError:
            chosen = -1
        answers[str(i)] = chosen
        correct_index = int(q.get("answer_index", -1))
        if chosen == correct_index:
            score += 1
    attempt = QuizAttempt.objects.create(quiz=quiz, answers=answers, score=score, total=len(quiz.questions))
    review = []
    for i, q in enumerate(quiz.questions):
        idx = int(q.get("answer_index", -1))
        options = q.get("options", [])
        if not options or not 0 <= idx < len(options):
            continue
        chosen = answers.get(str(i), -1)
        review.append({"question": q.get("question", "سؤال"), "correct_answer": options[idx], "chosen_answer": options[chosen] if 0 <= chosen < len(options) else "بدون پاسخ", "is_correct": chosen == idx, "explanation": q.get("explanation", "")})
    return render(request, "core/quiz_result.html", {"quiz": quiz, "attempt": attempt, "review": review})

@onboarding_required
def portfolio(request):
    profile = UserProfile.objects.get_or_create(user=request.user, defaults={"display_name": request.user.username})[0]
    projects = CodeProject.objects.filter(user=request.user, status="done").order_by("-updated_at")
    completed_missions = Mission.objects.filter(user=request.user, completed=True).order_by("-completed_at", "-created_at")
    all_skills = {}
    for mission in Mission.objects.filter(user=request.user):
        row = all_skills.setdefault(mission.skill, {"name": mission.skill, "total": 0, "done": 0, "xp": 0})
        row["total"] += 1
        if mission.completed:
            row["done"] += 1
            row["xp"] += mission.xp
    skills = sorted(all_skills.values(), key=lambda row: (-row["done"], row["name"]))
    completed_skills = [row for row in skills if row["total"] > 0 and row["done"] == row["total"]]
    return render(request, "core/portfolio.html", {
        "profile": profile, "projects": projects, "completed_missions": completed_missions,
        "skills": skills, "completed_skills": completed_skills,
        "completed_count": completed_missions.count(),
        "total_xp": sum(m.xp for m in completed_missions),
    })

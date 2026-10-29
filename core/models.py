from django.db import models
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
import os
import base64
import hashlib

def _fernet():
    key = os.getenv("NEXORA_ENCRYPTION_KEY", "").strip()
    if key and key != "replace-with-generated-fernet-key":
        try:
            return Fernet(key.encode())
        except (TypeError, ValueError) as exc:
            raise ValueError("NEXORA_ENCRYPTION_KEY معتبر نیست.") from exc
    if not settings.DEBUG:
        raise ValueError("در محیط production باید NEXORA_ENCRYPTION_KEY مستقل تنظیم شود.")
    secret = str(settings.SECRET_KEY).encode("utf-8")
    if not secret or secret == b"dev-only-change-me-before-deploying" or secret.startswith(b"replace-"):
        raise ValueError("ابتدا DJANGO_SECRET_KEY را در فایل .env تغییر بده.")
    derived = base64.urlsafe_b64encode(hashlib.sha256(b"Nexora API key encryption v1:" + secret).digest())
    return Fernet(derived)

class AIConfig(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="nexora_ai_configs")
    PROVIDERS = [
        ("openrouter", "OpenRouter"),
        ("openai_compatible", "OpenAI-compatible API"),
        ("anthropic", "Anthropic Claude API"),
        ("gemini", "Google Gemini API"),
    ]
    name = models.CharField(max_length=80, default="My AI mentor")
    provider = models.CharField(max_length=32, choices=PROVIDERS, default="openai_compatible")
    base_url = models.URLField(max_length=500, blank=True, default="https://openrouter.ai/api/v1")
    model = models.CharField(max_length=160, default="openai/gpt-4o-mini")
    encrypted_api_key = models.TextField(blank=True, default="")
    system_prompt = models.TextField(default=(
        "You are Nexora, a kind and practical programming mentor. Help the learner become independent. "
        "First understand their level and goal. Break projects into small milestones. Prefer hints before full solutions, "
        "explain errors simply, ask the learner to try, and never claim code was executed unless a tool actually ran it. "
        "Give accurate, safe, beginner-friendly advice. If asked for a project, define goal, requirements, milestones, "
        "acceptance criteria, and what the learner should learn. Keep answers structured and concise."
    ))
    is_active = models.BooleanField(default=True)
    
    temperature = models.FloatField(default=0.4)
    max_output_tokens = models.PositiveIntegerField(default=1200)
    daily_ai_limit = models.PositiveIntegerField(default=40)
    mentor_mode = models.CharField(max_length=24, choices=[("coach", "Coach / hints first"), ("direct", "Direct answers"), ("socratic", "Socratic questions")], default="coach")
    auto_notify_agent = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_api_key(self, raw):
        raw = (raw or "").strip()
        if not raw:
            return
        f = _fernet()
        if f is None:
            raise ValueError("کلید رمزنگاری تنظیم نشده است. فایل .env را طبق README تنظیم کن.")
        self.encrypted_api_key = f.encrypt(raw.encode()).decode()

    def get_api_key(self):
        if not self.encrypted_api_key:
            return ""
        f = _fernet()
        if f is None:
            return ""
        try:
            return f.decrypt(self.encrypted_api_key.encode()).decode()
        except (InvalidToken, ValueError):
            return ""

    def __str__(self):
        return f"{self.name} ({self.model})"

class Mission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="mission_items")
    title = models.CharField(max_length=180)
    description = models.TextField()
    difficulty = models.CharField(max_length=24, default="شروع")
    skill = models.CharField(max_length=80, default="Python")
    xp = models.PositiveIntegerField(default=30)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["completed", "-created_at"]

    def __str__(self):
        return self.title

class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="chatmessage_items")
    ROLE_CHOICES = [("user", "User"), ("assistant", "Assistant")]
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class UserProfile(models.Model):
    LEVELS = [("مبتدی", "مبتدی"), ("متوسط", "متوسط"), ("پیشرفته", "پیشرفته")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="nexora_profile")
    display_name = models.CharField(max_length=80, blank=True, default="")
    interests = models.JSONField(default=list, blank=True)
    current_level = models.CharField(max_length=40, choices=LEVELS, default="مبتدی")
    daily_minutes = models.PositiveIntegerField(default=30)
    main_goal = models.CharField(max_length=240, default="ساخت پروژه‌های واقعی")
    onboarding_complete = models.BooleanField(default=False)
    theme = models.CharField(max_length=24, default="aurora")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def preferred_topics(self):
        return ",".join(self.interests)

    def __str__(self):
        return f"{self.user.username} — Nexora profile"

class LearningProfile(models.Model):
    """Single local learner profile; this MVP is intentionally single-user."""
    display_name = models.CharField(max_length=80, default="Developer")
    main_goal = models.CharField(max_length=240, default="ساخت پروژه‌های واقعی با Python و Django")
    current_level = models.CharField(max_length=40, default="مبتدی")
    daily_minutes = models.PositiveIntegerField(default=45)
    preferred_topics = models.CharField(max_length=240, default="Python,Django,حل مسئله")
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def current(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return self.display_name

class LearningNote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="learningnote_items")
    title = models.CharField(max_length=180)
    content = models.TextField()
    topic = models.CharField(max_length=80, default="عمومی")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

class CodeProject(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="codeproject_items")
    STATUS_CHOICES = [("idea", "ایده"), ("active", "در حال انجام"), ("done", "تکمیل‌شده")]
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=60, default="Python")
    code = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="idea")
    estimated_minutes = models.PositiveIntegerField(default=120, help_text="تخمین زمان لازم برای تکمیل پروژه به دقیقه")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def duration_label(self):
        minutes = max(0, int(self.estimated_minutes or 0))
        hours, remainder = divmod(minutes, 60)
        if hours and remainder:
            return f"{hours} ساعت و {remainder} دقیقه"
        if hours:
            return f"{hours} ساعت"
        return f"{remainder} دقیقه"

    class Meta:
        ordering = ["-updated_at"]

class DailyPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="dailyplan_items")
    plan_date = models.DateField()
    title = models.CharField(max_length=180, default="برنامه یادگیری امروز")
    items = models.JSONField(default=list, blank=True)
    generated_by_ai = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-plan_date"]
        constraints = [models.UniqueConstraint(fields=["user", "plan_date"], name="unique_user_daily_plan")]

class Quiz(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="quiz_items")
    title = models.CharField(max_length=180)
    topic = models.CharField(max_length=100, default="Python")
    questions = models.JSONField(default=list)  
    generated_by_ai = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    answers = models.JSONField(default=dict)
    score = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class AgentNotice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="agentnotice_items")
    kind = models.CharField(max_length=40, default="mission_created")
    title = models.CharField(max_length=180)
    detail = models.TextField(blank=True)
    delivered_to_agent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class LearningPath(models.Model):
    """An AI-generated learning roadmap owned by one learner."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_paths")
    topic = models.CharField(max_length=100)
    title = models.CharField(max_length=180)
    overview = models.TextField(blank=True)
    steps = models.JSONField(default=list, blank=True)
    generated_by_ai = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [models.UniqueConstraint(fields=["user", "topic"], name="unique_user_learning_path_topic")]

    @property
    def completed_steps(self):
        return sum(1 for step in self.steps if isinstance(step, dict) and step.get("completed"))

    @property
    def progress_percent(self):
        if not self.steps:
            return 0
        return round(self.completed_steps * 100 / len(self.steps))

    def __str__(self):
        return f"{self.user} — {self.topic}"

class AIUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="nexora_ai_usage")
    day = models.DateField()
    calls = models.PositiveIntegerField(default=0)
    estimated_prompt_chars = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "day"], name="unique_user_ai_usage_day")]

    @classmethod
    def today(cls, user=None):
        from django.utils import timezone
        obj, _ = cls.objects.get_or_create(user=user, day=timezone.localdate())
        return obj

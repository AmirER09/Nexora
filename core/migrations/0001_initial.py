from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="AIConfig", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(default="My AI mentor", max_length=80)),
            ("provider", models.CharField(choices=[("openrouter", "OpenRouter"), ("openai_compatible", "OpenAI-compatible API"), ("gemini", "Google Gemini API")], default="openai_compatible", max_length=32)),
            ("base_url", models.URLField(blank=True, default="https://openrouter.ai/api/v1", max_length=500)),
            ("model", models.CharField(default="openai/gpt-4o-mini", max_length=160)),
            ("encrypted_api_key", models.TextField(blank=True, default="")),
            ("system_prompt", models.TextField(default="You are Nexora, a kind and practical programming mentor. Help the learner become independent. First understand their level and goal. Break projects into small milestones. Prefer hints before full solutions, explain errors simply, ask the learner to try, and never claim code was executed unless a tool actually ran it. Give accurate, safe, beginner-friendly advice. If asked for a project, define goal, requirements, milestones, acceptance criteria, and what the learner should learn. Keep answers structured and concise.")),
            ("is_active", models.BooleanField(default=True)), ("temperature", models.FloatField(default=0.4)),
            ("max_output_tokens", models.PositiveIntegerField(default=1200)), ("daily_ai_limit", models.PositiveIntegerField(default=40)),
            ("mentor_mode", models.CharField(choices=[("coach", "Coach / hints first"), ("direct", "Direct answers"), ("socratic", "Socratic questions")], default="coach", max_length=24)),
            ("auto_notify_agent", models.BooleanField(default=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(name="Mission", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=180)), ("description", models.TextField()),
            ("difficulty", models.CharField(default="شروع", max_length=24)), ("skill", models.CharField(default="Python", max_length=80)),
            ("xp", models.PositiveIntegerField(default=30)), ("completed", models.BooleanField(default=False)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("completed_at", models.DateTimeField(blank=True, null=True)),
        ], options={"ordering": ["completed", "-created_at"]}),
        migrations.CreateModel(name="ChatMessage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant")], max_length=12)),
            ("content", models.TextField()), ("created_at", models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name="LearningProfile", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("display_name", models.CharField(default="Developer", max_length=80)),
            ("main_goal", models.CharField(default="ساخت پروژه‌های واقعی با Python و Django", max_length=240)),
            ("current_level", models.CharField(default="مبتدی", max_length=40)), ("daily_minutes", models.PositiveIntegerField(default=45)),
            ("preferred_topics", models.CharField(default="Python,Django,حل مسئله", max_length=240)), ("updated_at", models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(name="LearningNote", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=180)), ("content", models.TextField()), ("topic", models.CharField(default="عمومی", max_length=80)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ], options={"ordering": ["-updated_at"]}),
        migrations.CreateModel(name="CodeProject", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=180)), ("description", models.TextField(blank=True)), ("language", models.CharField(default="Python", max_length=60)),
            ("code", models.TextField(blank=True)), ("status", models.CharField(choices=[("idea", "ایده"), ("active", "در حال انجام"), ("done", "تکمیل‌شده")], default="idea", max_length=16)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ], options={"ordering": ["-updated_at"]}),
        migrations.CreateModel(name="DailyPlan", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("plan_date", models.DateField()), ("title", models.CharField(default="برنامه یادگیری امروز", max_length=180)),
            ("items", models.JSONField(blank=True, default=list)), ("generated_by_ai", models.BooleanField(default=False)), ("created_at", models.DateTimeField(auto_now_add=True)),
        ], options={"ordering": ["-plan_date"]}),
        migrations.CreateModel(name="Quiz", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=180)), ("topic", models.CharField(default="Python", max_length=100)),
            ("questions", models.JSONField(default=list)), ("created_at", models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name="QuizAttempt", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("answers", models.JSONField(default=dict)), ("score", models.PositiveIntegerField(default=0)), ("total", models.PositiveIntegerField(default=0)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("quiz", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="core.quiz")),
        ]),
        migrations.CreateModel(name="AgentNotice", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("kind", models.CharField(default="mission_created", max_length=40)), ("title", models.CharField(max_length=180)),
            ("detail", models.TextField(blank=True)), ("delivered_to_agent", models.BooleanField(default=False)), ("created_at", models.DateTimeField(auto_now_add=True)),
        ], options={"ordering": ["-created_at"]}),
        migrations.CreateModel(name="AIUsage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("day", models.DateField()), ("calls", models.PositiveIntegerField(default=0)),
            ("estimated_prompt_chars", models.PositiveIntegerField(default=0)), ("updated_at", models.DateTimeField(auto_now=True)),
        ]),
    ]

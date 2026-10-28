from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="UserProfile", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("display_name", models.CharField(blank=True, default="", max_length=80)),
            ("interests", models.JSONField(blank=True, default=list)),
            ("current_level", models.CharField(choices=[("مبتدی", "مبتدی"), ("متوسط", "متوسط"), ("پیشرفته", "پیشرفته")], default="مبتدی", max_length=40)),
            ("daily_minutes", models.PositiveIntegerField(default=30)),
            ("main_goal", models.CharField(default="ساخت پروژه‌های واقعی", max_length=240)),
            ("onboarding_complete", models.BooleanField(default=False)),
            ("theme", models.CharField(default="aurora", max_length=24)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="nexora_profile", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddField(model_name="mission", name="user", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="mission_items", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="chatmessage", name="user", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="chatmessage_items", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="learningnote", name="user", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="learningnote_items", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="codeproject", name="user", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="codeproject_items", to=settings.AUTH_USER_MODEL)),
        migrations.AlterField(model_name="dailyplan", name="plan_date", field=models.DateField()),
        migrations.AddField(model_name="dailyplan", name="user", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="dailyplan_items", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="quiz", name="user", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="quiz_items", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="agentnotice", name="user", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="agentnotice_items", to=settings.AUTH_USER_MODEL)),
        migrations.AddConstraint(model_name="dailyplan", constraint=models.UniqueConstraint(fields=("user", "plan_date"), name="unique_user_daily_plan")),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0004_quiz_generated_by_ai")]

    operations = [
        migrations.AddField(
            model_name="codeproject",
            name="estimated_minutes",
            field=models.PositiveIntegerField(default=120, help_text="تخمین زمان لازم برای تکمیل پروژه به دقیقه"),
        ),
    ]

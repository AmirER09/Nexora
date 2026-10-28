from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0005_project_estimated_minutes")]

    operations = [
        migrations.AlterField(
            model_name="aiconfig",
            name="provider",
            field=models.CharField(
                choices=[
                    ("openrouter", "OpenRouter"),
                    ("openai_compatible", "OpenAI-compatible API"),
                    ("anthropic", "Anthropic Claude API"),
                    ("gemini", "Google Gemini API"),
                ],
                default="openai_compatible",
                max_length=32,
            ),
        ),
    ]

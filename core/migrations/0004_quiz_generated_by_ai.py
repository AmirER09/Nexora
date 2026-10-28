from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0003_per_user_ai")]

    operations = [
        migrations.AddField(
            model_name="quiz",
            name="generated_by_ai",
            field=models.BooleanField(default=False),
        ),
    ]

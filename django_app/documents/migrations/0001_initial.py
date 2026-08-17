from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DocumentGraph",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(blank=True, max_length=500)),
                ("source_file", models.FileField(upload_to="uploads/")),
                ("graph_file", models.FileField(blank=True, upload_to="graphs/")),
                ("summary_file", models.FileField(blank=True, upload_to="summaries/")),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("READY", "Ready"), ("FAILED", "Failed")], default="PENDING", max_length=20)),
                ("triple_count", models.PositiveIntegerField(default=0)),
                ("paragraph_count", models.PositiveIntegerField(default=0)),
                ("section_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentgraph",
            name="fuseki_dataset",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="documentgraph",
            name="graph_uri",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="documentgraph",
            name="storage_backend",
            field=models.CharField(choices=[("FUSEKI", "Fuseki"), ("FILE", "File")], default="FUSEKI", max_length=20),
        ),
    ]

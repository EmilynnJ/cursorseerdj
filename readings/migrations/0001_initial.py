from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='Session',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modality', models.CharField(choices=[('text', 'Text'), ('voice', 'Voice'), ('video', 'Video')], default='voice', max_length=20)),
                ('state', models.CharField(choices=[('created', 'Created'), ('waiting', 'Waiting'), ('active', 'Active'), ('paused', 'Paused'), ('reconnecting', 'Reconnecting'), ('ended', 'Ended'), ('finalized', 'Finalized')], db_index=True, default='created', max_length=20)),
                ('channel_name', models.CharField(blank=True, db_index=True, max_length=255)),
                ('rate_per_minute', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=8)),
                ('billing_minutes', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('last_billing_at', models.DateTimeField(blank=True, null=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='client_sessions', to=settings.AUTH_USER_MODEL)),
                ('reader', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reader_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]

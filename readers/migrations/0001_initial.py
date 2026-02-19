from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='ReaderProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(db_index=True, unique=True)),
                ('bio', models.TextField(blank=True)),
                ('avatar_url', models.URLField(blank=True)),
                ('specialties', models.CharField(blank=True, help_text='Comma-separated tags', max_length=500)),
                ('is_verified', models.BooleanField(default=False)),
                ('stripe_connect_account_id', models.CharField(blank=True, db_index=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='reader_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ReaderRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modality', models.CharField(choices=[('text', 'Text'), ('voice', 'Voice'), ('video', 'Video')], max_length=20)),
                ('rate_per_minute', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=8)),
                ('reader', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rates', to='readers.readerprofile')),
            ],
            options={'unique_together': {('reader', 'modality')}},
        ),
        migrations.CreateModel(
            name='ReaderAvailability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day_of_week', models.PositiveSmallIntegerField(help_text='0=Monday, 6=Sunday')),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('reader', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='availability', to='readers.readerprofile')),
            ],
            options={'verbose_name_plural': 'Reader availabilities'},
        ),
    ]

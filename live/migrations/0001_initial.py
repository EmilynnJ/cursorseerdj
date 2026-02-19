from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wallets', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Livestream',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('visibility', models.CharField(choices=[('public', 'Public'), ('private', 'Private'), ('premium', 'Premium')], default='public', max_length=20)),
                ('agora_channel', models.CharField(blank=True, db_index=True, max_length=255)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('reader', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='livestreams', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Gift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('price', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=8)),
                ('animation_id', models.CharField(blank=True, max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='GiftPurchase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('gift', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='live.gift')),
                ('ledger_entry', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='wallets.ledgerentry')),
                ('livestream', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gifts', to='live.livestream')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gift_purchases', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

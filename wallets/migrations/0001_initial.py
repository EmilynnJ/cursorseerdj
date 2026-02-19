from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('readings', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12)),
                ('stripe_customer_id', models.CharField(blank=True, db_index=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='wallet', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ProcessedStripeEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_event_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='LedgerEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('entry_type', models.CharField(choices=[('top_up', 'Top Up'), ('session_charge', 'Session Charge'), ('booking', 'Booking'), ('paid_reply', 'Paid Reply'), ('gift', 'Gift'), ('refund', 'Refund'), ('adjustment', 'Adjustment'), ('payout', 'Payout'), ('commission', 'Commission')], max_length=20)),
                ('idempotency_key', models.CharField(db_index=True, max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('stripe_payment_intent_id', models.CharField(blank=True, db_index=True, max_length=255)),
                ('stripe_event_id', models.CharField(blank=True, db_index=True, max_length=255)),
                ('reference_type', models.CharField(blank=True, max_length=50)),
                ('reference_id', models.CharField(blank=True, max_length=255)),
                ('session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ledger_entries', to='readings.session')),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='wallets.wallet')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]

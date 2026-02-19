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
            name='ScheduledSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField()),
                ('end', models.DateTimeField()),
                ('duration_minutes', models.PositiveSmallIntegerField(default=30)),
                ('status', models.CharField(choices=[('available', 'Available'), ('booked', 'Booked'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], db_index=True, default='available', max_length=20)),
                ('client', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='booked_slots', to=settings.AUTH_USER_MODEL)),
                ('reader', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_slots', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['start']},
        ),
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to=settings.AUTH_USER_MODEL)),
                ('ledger_entry', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='booking', to='wallets.ledgerentry')),
                ('slot', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='booking', to='scheduling.scheduledslot')),
            ],
        ),
    ]

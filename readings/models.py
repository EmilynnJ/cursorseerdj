from decimal import Decimal
from django.conf import settings
from django.db import models

SESSION_STATES = [
    ('created', 'Created'),
    ('waiting', 'Waiting'),
    ('active', 'Active'),
    ('paused', 'Paused'),
    ('reconnecting', 'Reconnecting'),
    ('ended', 'Ended'),
    ('finalized', 'Finalized'),
]

MODALITY_CHOICES = [
    ('text', 'Text'),
    ('voice', 'Voice'),
    ('video', 'Video'),
]


class Session(models.Model):
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_sessions',
    )
    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reader_sessions',
    )
    modality = models.CharField(max_length=20, choices=MODALITY_CHOICES, default='voice')
    state = models.CharField(max_length=20, choices=SESSION_STATES, default='created', db_index=True)
    channel_name = models.CharField(max_length=255, blank=True, db_index=True)
    rate_per_minute = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    billing_minutes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    last_billing_at = models.DateTimeField(null=True, blank=True)
    grace_until = models.DateTimeField(null=True, blank=True, help_text='Reconnection grace deadline')
    reconnect_count = models.PositiveIntegerField(default=0)
    summary = models.TextField(blank=True, help_text='Session summary recorded on end')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.pk} ({self.state})"

    def transition(self, new_state):
        valid = {
            'created': ['waiting'],
            'waiting': ['active', 'ended'],
            'active': ['paused', 'ended'],
            'paused': ['reconnecting', 'active', 'ended'],
            'reconnecting': ['active', 'ended'],
            'ended': ['finalized'],
        }
        if new_state in valid.get(self.state, []):
            self.state = new_state
            self.save(update_fields=['state'])
            return True
        return False


class SessionNote(models.Model):
    """Client notes about a session or reader."""
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_notes',
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notes',
    )
    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notes_about_me',
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

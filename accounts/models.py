from django.conf import settings
from django.db import models

ROLE_CHOICES = [
    ('client', 'Client'),
    ('reader', 'Reader'),
    ('admin', 'Admin'),
]


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    auth0_sub = models.CharField(max_length=255, unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    display_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email or self.user.username} ({self.role})"

    @property
    def is_client(self):
        return self.role == 'client'

    @property
    def is_reader(self):
        return self.role == 'reader'

    @property
    def is_admin(self):
        return self.role == 'admin'

    def get_role_display(self):
        return dict(ROLE_CHOICES).get(self.role, self.role)

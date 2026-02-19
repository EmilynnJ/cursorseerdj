from decimal import Decimal
from django.conf import settings
from django.db import models
from django.urls import reverse

MODALITY_CHOICES = [
    ('text', 'Text'),
    ('voice', 'Voice'),
    ('video', 'Video'),
]


class ReaderProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reader_profile'
    )
    slug = models.SlugField(unique=True, db_index=True)
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    specialties = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags')
    is_verified = models.BooleanField(default=False)
    stripe_connect_account_id = models.CharField(max_length=255, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.slug or str(self.user)

    def get_absolute_url(self):
        return reverse('reader_detail', kwargs={'slug': self.slug})

    def get_specialties_list(self):
        if not self.specialties:
            return []
        return [s.strip() for s in self.specialties.split(',') if s.strip()]


class ReaderRate(models.Model):
    reader = models.ForeignKey(ReaderProfile, on_delete=models.CASCADE, related_name='rates')
    modality = models.CharField(max_length=20, choices=MODALITY_CHOICES)
    rate_per_minute = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))

    class Meta:
        unique_together = [('reader', 'modality')]

    def __str__(self):
        return f"{self.reader.slug} {self.modality} ${self.rate_per_minute}/min"


class ReaderAvailability(models.Model):
    reader = models.ForeignKey(ReaderProfile, on_delete=models.CASCADE, related_name='availability')
    day_of_week = models.PositiveSmallIntegerField(help_text='0=Monday, 6=Sunday')
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        verbose_name_plural = 'Reader availabilities'


class Review(models.Model):
    reader = models.ForeignKey(ReaderProfile, on_delete=models.CASCADE, related_name='reviews')
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reader_reviews',
    )
    session = models.ForeignKey(
        'readings.Session',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
    )
    rating = models.PositiveSmallIntegerField()  # 1-5
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Favorite(models.Model):
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_readers',
    )
    reader = models.ForeignKey(ReaderProfile, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('client', 'reader')]

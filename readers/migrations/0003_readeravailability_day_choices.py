from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('readers', '0002_review_favorite'),
    ]

    operations = [
        migrations.AlterField(
            model_name='readeravailability',
            name='day_of_week',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
                    (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
                ],
                help_text='0=Monday, 6=Sunday',
            ),
        ),
    ]

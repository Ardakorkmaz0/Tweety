from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tweetapp', '0037_gamescore'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='theme_preference',
            field=models.CharField(choices=[('dark', 'Dark'), ('light', 'Light')], default='dark', max_length=10),
        ),
    ]

# Generated by Django 2.1.2 on 2019-06-02 16:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blogsite', '0018_merge_20190530_2018'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_online',
            field=models.BooleanField(default=False),
        ),
    ]

# Generated by Django 2.1.2 on 2021-09-07 16:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0010_auto_20210905_1315'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='time_per_question',
            field=models.IntegerField(blank=True, default=30, null=True),
        ),
        migrations.AddField(
            model_name='contest',
            name='valid_for',
            field=models.IntegerField(blank=True, default=20, null=True),
        ),
    ]
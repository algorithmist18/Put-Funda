# Generated by Django 2.1.2 on 2019-05-24 19:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blogsite', '0010_auto_20190525_0033'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='question',
            field=models.TextField(default='What is life?'),
        ),
    ]

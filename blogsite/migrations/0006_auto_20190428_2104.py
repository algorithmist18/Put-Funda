# Generated by Django 2.1.2 on 2019-04-28 15:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blogsite', '0005_auto_20190428_2100'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='question',
            field=models.ForeignKey(default='What is life?', on_delete=django.db.models.deletion.CASCADE, to='blogsite.Question'),
        ),
    ]

# Generated by Django 2.1.2 on 2019-05-30 12:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blogsite', '0015_auto_20190530_1822'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='question',
            field=models.ForeignKey(default='What is life?', on_delete=django.db.models.deletion.DO_NOTHING, to='blogsite.Question'),
        ),
    ]

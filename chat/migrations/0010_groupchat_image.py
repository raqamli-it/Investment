# Generated by Django 5.1.6 on 2025-03-07 17:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0009_groupmessageread'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupchat',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='group_images/'),
        ),
    ]

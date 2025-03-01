# Generated by Django 4.2.1 on 2024-11-05 11:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0003_remove_smartnotemedia_media_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='note_images/')),
                ('smart_note', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='data.smartnote')),
            ],
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('video', models.FileField(upload_to='note_videos/')),
                ('smart_note', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='videos', to='data.smartnote')),
            ],
        ),
        migrations.DeleteModel(
            name='SmartNoteMedia',
        ),
    ]

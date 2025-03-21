# Generated by Django 4.2.1 on 2024-11-03 18:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SmartNoteMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('audio', 'Audio')], max_length=10)),
                ('file', models.FileField(upload_to='note_media/')),
                ('smart_note', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media_files', to='data.smartnote')),
            ],
        ),
    ]

# Generated by Django 4.2.1 on 2024-10-22 15:42

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AllData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('Draft', 'Draft'), ('Checking', 'Checking'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Draft', max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.CharField(max_length=150)),
                ('location_ru', models.CharField(max_length=150, null=True)),
                ('location_uz', models.CharField(max_length=150, null=True)),
                ('location_en', models.CharField(max_length=150, null=True)),
                ('lat', models.DecimalField(decimal_places=18, default=0, max_digits=22)),
                ('long', models.DecimalField(decimal_places=18, default=0, max_digits=22)),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(max_length=256)),
                ('category_ru', models.CharField(max_length=256, null=True)),
                ('category_uz', models.CharField(max_length=256, null=True)),
                ('category_en', models.CharField(max_length=256, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=4)),
                ('name', models.CharField(max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='Faq',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('files', models.FileField(upload_to='files/faq')),
            ],
        ),
        migrations.CreateModel(
            name='InformativeData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_info', models.CharField(default='', max_length=256)),
                ('project_capacity', models.CharField(default='', max_length=30)),
                ('formation_date', models.DateTimeField(blank=True, null=True)),
                ('total_area', models.DecimalField(decimal_places=0, default=0, max_digits=6)),
                ('building_area', models.DecimalField(decimal_places=0, default=0, max_digits=6)),
                ('tech_equipment', models.CharField(default='', max_length=30)),
                ('is_validated', models.BooleanField(default=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='informative_data', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='MainData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enterprise_name', models.CharField(default='', max_length=30)),
                ('legal_form', models.CharField(default='', max_length=30)),
                ('lat', models.DecimalField(decimal_places=18, default=0, max_digits=22)),
                ('long', models.DecimalField(decimal_places=18, default=0, max_digits=22)),
                ('field_of_activity', models.CharField(default='', max_length=30)),
                ('infrastructure', models.CharField(default='', max_length=30)),
                ('project_staff', models.DecimalField(decimal_places=0, default=0, max_digits=4)),
                ('is_validated', models.BooleanField(default=True)),
                ('category', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='main_data', to='data.category')),
                ('location', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='main_data', to='data.area')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='main_data', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SmartNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(default='')),
                ('name', models.CharField(blank=True, max_length=128, null=True)),
                ('custom_id', models.CharField(blank=True, max_length=30, null=True)),
                ('create_date_note', models.DateTimeField(blank=True, null=True)),
                ('main_data', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='smart_notes', to='data.maindata')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='smart_notes', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ProductPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.FileField(upload_to='files/product_photo/')),
                ('informative_data', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_photo_list', to='data.informativedata')),
            ],
        ),
        migrations.CreateModel(
            name='ObjectPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='files/object_photo/')),
                ('informative_data', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='object_foto', to='data.informativedata')),
            ],
        ),
        migrations.CreateModel(
            name='InvestorInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_name', models.CharField(default='', max_length=128)),
                ('email', models.EmailField(default='', max_length=254)),
                ('user_phone', phonenumber_field.modelfields.PhoneNumberField(blank=True, default='', max_length=128, null=True, region=None, verbose_name='Phone number')),
                ('message', models.TextField(default='')),
                ('file', models.FileField(upload_to='files/investment')),
                ('status', models.CharField(choices=[('Draft', 'Draft'), ('Checking', 'Checking'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Draft', max_length=10)),
                ('date_created', models.DateTimeField(blank=True, default=None, null=True)),
                ('all_data', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investment', to='data.alldata')),
                ('investor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investor', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='FinancialData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('export_share', models.DecimalField(decimal_places=4, default=0, max_digits=18)),
                ('authorized_capital', models.DecimalField(decimal_places=4, default=0, max_digits=18)),
                ('estimated_value', models.DecimalField(decimal_places=4, default=0, max_digits=18)),
                ('investment_or_loan_amount', models.DecimalField(decimal_places=4, default=0, max_digits=18)),
                ('investment_direction', models.CharField(default='', max_length=30)),
                ('major_shareholders', models.CharField(default='', max_length=30)),
                ('is_validated', models.BooleanField(default=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='financial_data', to='data.currency')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='financial_data', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CurrencyPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=4)),
                ('name', models.CharField(max_length=30)),
                ('cb_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('date', models.DateField(auto_now=True)),
                ('currency', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='prices', to='data.currency')),
            ],
        ),
        migrations.CreateModel(
            name='CadastralPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.FileField(upload_to='files/cadastral_photo/')),
                ('informative_data', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cadastral_info_list', to='data.informativedata')),
            ],
        ),
        migrations.AddField(
            model_name='alldata',
            name='financial_data',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='all_data', to='data.financialdata'),
        ),
        migrations.AddField(
            model_name='alldata',
            name='informative_data',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='all_data', to='data.informativedata'),
        ),
        migrations.AddField(
            model_name='alldata',
            name='main_data',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='all_data', to='data.maindata'),
        ),
        migrations.AddField(
            model_name='alldata',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='all_data', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='AllDataReady',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('data.alldata',),
        ),
    ]

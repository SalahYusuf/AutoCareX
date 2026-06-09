from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Vehicle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nickname', models.CharField(max_length=100)),
                ('model', models.CharField(choices=[('EMAS 5', 'Proton e.MAS 5'), ('EMAS 7', 'Proton e.MAS 7'), ('EMAS PHEV', 'Proton e.MAS PHEV')], default='EMAS 5', max_length=20)),
                ('year', models.PositiveIntegerField(default=2024)),
                ('mileage', models.PositiveIntegerField(default=0, help_text='Total mileage in km')),
                ('battery_percent', models.PositiveIntegerField(default=100, help_text='Current battery %')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vehicles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]

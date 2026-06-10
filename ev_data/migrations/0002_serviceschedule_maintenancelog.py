from django.db import migrations, models
import django.db.models.deletion
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('ev_data', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServiceSchedule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('component', models.CharField(choices=[('battery','Battery Health'),('tyre','Tyre'),('brake','Brake'),('coolant','Coolant System'),('general','General Service')], max_length=20)),
                ('interval_km', models.PositiveIntegerField()),
                ('interval_months', models.PositiveIntegerField()),
                ('last_service_km', models.PositiveIntegerField(blank=True, null=True)),
                ('last_service_date', models.DateField(blank=True, null=True)),
                ('next_due_km', models.PositiveIntegerField(blank=True, null=True)),
                ('next_due_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedules', to='ev_data.vehicle')),
            ],
            options={'ordering': ['component'], 'unique_together': {('vehicle', 'component')}},
        ),
        migrations.CreateModel(
            name='MaintenanceLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('component', models.CharField(max_length=20)),
                ('description', models.TextField(blank=True)),
                ('odometer', models.PositiveIntegerField()),
                ('service_date', models.DateField(default=datetime.date.today)),
                ('cost', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='ev_data.vehicle')),
                ('schedule', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='logs', to='ev_data.serviceschedule')),
            ],
            options={'ordering': ['-service_date', '-created_at']},
        ),
    ]

from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import date
from dateutil.relativedelta import relativedelta

# ── Vehicle ────────────────────────────────────────────────────────────────────

class Vehicle(models.Model):

    MODEL_CHOICES = [
        ('EMAS 5',    'Proton e.MAS 5'),
        ('EMAS 7',    'Proton e.MAS 7'),
        ('EMAS PHEV', 'Proton e.MAS PHEV'),
    ]

    owner           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicles')
    nickname        = models.CharField(max_length=100)
    model           = models.CharField(max_length=20, choices=MODEL_CHOICES, default='EMAS 5')
    year            = models.PositiveIntegerField(default=2024)
    mileage         = models.PositiveIntegerField(default=0, help_text='Total mileage in km')
    battery_percent = models.PositiveIntegerField(default=100, help_text='Current battery %')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.nickname} ({self.model})"

    @property
    def dot_label(self):
        labels = {'EMAS 5': 'e5', 'EMAS 7': 'e7', 'EMAS PHEV': 'PH'}
        return labels.get(self.model, 'EV')

    @property
    def dot_class(self):
        classes = {'EMAS 5': 'dot-5', 'EMAS 7': 'dot-7', 'EMAS PHEV': 'dot-phev'}
        return classes.get(self.model, 'dot-5')
    
    def get_image(self):
        images = {
            "EMAS 5": "image/emas5transparent.png",
            "EMAS 7": "image/emas7transparent.png",
            "EMAS PHEV": "image/emasphevtransparent.png",
        }
        return images.get(self.model, "image/emas5transparent.png")
    
    def get_engine_image(self):
        engines = {
            "EMAS 5": "image/emas5engine1.png",
            "EMAS 7": "image/emas7engine1.png",
            "EMAS PHEV": "image/emasphevengine1.png",
        }
        return engines.get(self.model, "image/emas5engine1.png")
    
    def max_range(self):
        ranges = {
        "EMAS 5": 325,
        "EMAS 7": 410,
        "EMAS PHEV": 996,
        }
        return ranges.get(self.model, 300)


    def estimate_range(self):
        return round(self.max_range() * self.battery_percent / 100)

# ── ServiceSchedule ────────────────────────────────────────────────────────────

class ServiceSchedule(models.Model):

    last_reset_date = models.DateField(null=True, blank=True)
    last_reset_km = models.IntegerField(null=True, blank=True)

    COMPONENT_CHOICES = [
        ('battery', 'Battery'),
        ('coolant', 'Coolant'),
        ('gear_oil', 'Gear Oil / Transmission'),
        ('brake', 'Brake'),
        ('tyre', 'Tyre'),
    ]

    vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name='schedules'
    )

    component = models.CharField(max_length=20, choices=COMPONENT_CHOICES)

    interval_km = models.PositiveIntegerField()
    interval_months = models.PositiveIntegerField()

    last_service_km = models.PositiveIntegerField(null=True, blank=True)
    last_service_date = models.DateField(null=True, blank=True)

    next_due_km = models.PositiveIntegerField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # models.py

    status_percent = models.IntegerField(default=100)

    last_checked_km = models.IntegerField(
    null=True,
    blank=True
)

    last_checked_date = models.DateField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['component']
        unique_together = ('vehicle', 'component')

    def __str__(self):
        return f"{self.vehicle.nickname} — {self.get_component_display()}"

    def save(self, *args, **kwargs):
        self.compute_next_due()
        super().save(*args, **kwargs)

    def compute_next_due(self):
        if self.last_service_km is not None:
            self.next_due_km = self.last_service_km + self.interval_km

        if self.last_service_date is not None:
            self.next_due_date = self.last_service_date + relativedelta(
                months=self.interval_months
            )

    # -------------------
    # ALERT SYSTEM
    # -------------------
    @property
    def alert_level(self):
        vehicle_km = self.vehicle.mileage
        today = date.today()

        km_overdue = self.next_due_km is not None and vehicle_km >= self.next_due_km
        date_overdue = self.next_due_date is not None and today >= self.next_due_date

        if km_overdue or date_overdue:
            return 'red'

        km_close = self.next_due_km is not None and vehicle_km >= (self.next_due_km - 1000)
        date_close = self.next_due_date is not None and (self.next_due_date - today).days <= 30

        if km_close or date_close:
            return 'yellow'

        return 'green'

    @property
    def alert_label(self):
        return {
            'green': 'Good',
            'yellow': 'Due Soon',
            'red': 'Overdue'
        }[self.alert_level]

    # -------------------
    # UI PROGRESS
    # -------------------
    @property
    def km_progress(self):
        if self.next_due_km is None or self.last_service_km is None:
            return None

        used = self.vehicle.mileage - self.last_service_km
        total = self.interval_km

        return min(max(int((used / total) * 100), 0), 100)

    @property
    def km_remaining(self):
        if self.next_due_km is None:
            return None
        return max(self.next_due_km - self.vehicle.mileage, 0)

    @property
    def days_remaining(self):
        if self.next_due_date is None:
            return None
        return max((self.next_due_date - date.today()).days, 0)

# ── MaintenanceLog ─────────────────────────────────────────────────────────────

class MaintenanceLog(models.Model):

    vehicle      = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='logs')
    schedule     = models.ForeignKey(ServiceSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    component    = models.CharField(max_length=20)
    description  = models.TextField(blank=True)
    odometer     = models.PositiveIntegerField(help_text='Odometer reading at service (km)')
    service_date = models.DateField(default=date.today)
    cost         = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-service_date', '-created_at']

    def __str__(self):
        return f"{self.vehicle.nickname} — {self.component} on {self.service_date}"

class Notification(models.Model):
    LEVEL_CHOICES = [
        ("normal", "Normal"),
        ("urgent", "Urgent"),
    ]

    TYPE_CHOICES = [
        ("maintenance", "Maintenance"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)

    component = models.CharField(max_length=20)
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)

    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    is_read = models.BooleanField(default=False)

    s_resolved = models.BooleanField(default=False)
     
    cycle_marker = models.CharField(max_length=100)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="normal")
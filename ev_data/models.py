from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import date


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


# ── ServiceSchedule ────────────────────────────────────────────────────────────

class ServiceSchedule(models.Model):

    COMPONENT_CHOICES = [
        ('battery',  'Battery Health'),
        ('tyre',     'Tyre'),
        ('brake',    'Brake'),
        ('coolant',  'Coolant System'),
        ('general',  'General Service'),
    ]

    vehicle          = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='schedules')
    component        = models.CharField(max_length=20, choices=COMPONENT_CHOICES)
    interval_km      = models.PositiveIntegerField(help_text='Service every X km')
    interval_months  = models.PositiveIntegerField(help_text='Service every X months')
    last_service_km  = models.PositiveIntegerField(null=True, blank=True)
    last_service_date = models.DateField(null=True, blank=True)
    next_due_km      = models.PositiveIntegerField(null=True, blank=True)
    next_due_date    = models.DateField(null=True, blank=True)
    is_active        = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['component']
        unique_together = ('vehicle', 'component')

    def __str__(self):
        return f"{self.vehicle.nickname} — {self.get_component_display()}"

    def compute_next_due(self):
        """Recalculate next_due_km and next_due_date from last service."""
        if self.last_service_km is not None:
            self.next_due_km = self.last_service_km + self.interval_km
        if self.last_service_date is not None:
            from dateutil.relativedelta import relativedelta
            self.next_due_date = self.last_service_date + relativedelta(months=self.interval_months)

    @property
    def alert_level(self):
        """Returns 'green', 'yellow', or 'red'."""
        vehicle_km = self.vehicle.mileage
        today      = date.today()
        km_overdue   = self.next_due_km   is not None and vehicle_km  >= self.next_due_km
        date_overdue = self.next_due_date is not None and today        >= self.next_due_date
        if km_overdue or date_overdue:
            return 'red'
        km_close   = self.next_due_km   is not None and vehicle_km  >= (self.next_due_km   - 1000)
        date_close = self.next_due_date is not None and (self.next_due_date - today).days <= 30
        if km_close or date_close:
            return 'yellow'
        return 'green'

    @property
    def alert_label(self):
        labels = {'green': 'Good', 'yellow': 'Due Soon', 'red': 'Overdue'}
        return labels[self.alert_level]

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

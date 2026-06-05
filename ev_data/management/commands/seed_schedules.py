"""
Usage: python manage.py seed_schedules
Seeds default EV service schedules for all vehicles that have none.
"""
from django.core.management.base import BaseCommand
from ev_data.models import Vehicle, ServiceSchedule

DEFAULTS = [
    {'component': 'battery',  'interval_km': 20000, 'interval_months': 12},
    {'component': 'tyre',     'interval_km': 10000, 'interval_months': 6},
    {'component': 'brake',    'interval_km': 20000, 'interval_months': 12},
    {'component': 'coolant',  'interval_km': 40000, 'interval_months': 24},
    {'component': 'general',  'interval_km': 10000, 'interval_months': 6},
]

class Command(BaseCommand):
    help = 'Seed default service schedules for all vehicles'

    def handle(self, *args, **kwargs):
        for vehicle in Vehicle.objects.all():
            for d in DEFAULTS:
                obj, created = ServiceSchedule.objects.get_or_create(
                    vehicle=vehicle,
                    component=d['component'],
                    defaults={
                        'interval_km': d['interval_km'],
                        'interval_months': d['interval_months'],
                    }
                )
                if created:
                    self.stdout.write(f"  Created: {vehicle.nickname} — {d['component']}")
        self.stdout.write(self.style.SUCCESS('Done seeding schedules.'))

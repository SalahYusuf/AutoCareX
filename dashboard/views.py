from datetime import date

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect, get_object_or_404

from ev_data.models import Vehicle, ServiceSchedule, MaintenanceLog

# Default schedules applied when a new vehicle is added
DEFAULT_SCHEDULES = [
    {'component': 'battery',  'interval_km': 20000, 'interval_months': 12},
    {'component': 'tyre',     'interval_km': 10000, 'interval_months': 6},
    {'component': 'brake',    'interval_km': 20000, 'interval_months': 12},
    {'component': 'coolant',  'interval_km': 40000, 'interval_months': 24},
    {'component': 'general',  'interval_km': 10000, 'interval_months': 6},
]


def _seed_schedules(vehicle):
    """Create default service schedules for a newly added vehicle."""
    for d in DEFAULT_SCHEDULES:
        ServiceSchedule.objects.get_or_create(
            vehicle=vehicle,
            component=d['component'],
            defaults={
                'interval_km':     d['interval_km'],
                'interval_months': d['interval_months'],
            }
        )


# ── Home ───────────────────────────────────────────────────────────────────────

def home(request):
    context = {}
    if request.user.is_authenticated:
        cars = Vehicle.objects.filter(owner=request.user)
        all_schedules = ServiceSchedule.objects.filter(
            vehicle__in=cars, is_active=True
        ).select_related('vehicle')
        context['alert_count']  = sum(1 for s in all_schedules if s.alert_level in ('yellow', 'red'))
        context['red_count']    = sum(1 for s in all_schedules if s.alert_level == 'red')
        context['cars']         = cars
        context['recent_logs']  = MaintenanceLog.objects.filter(
            vehicle__in=cars
        ).select_related('vehicle')[:5]
    return render(request, 'Home.html', context)


# ── Vehicle ────────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def vehicle(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_car':
            nickname = request.POST.get('nickname', '').strip()
            year     = request.POST.get('year', 2024)
            mileage  = request.POST.get('mileage', 0)
            model    = request.POST.get('model', 'EMAS 5')
            if not nickname:
                messages.error(request, 'Car nickname is required.')
            else:
                car = Vehicle.objects.create(
                    owner=request.user,
                    nickname=nickname,
                    year=int(year),
                    mileage=int(mileage),
                    model=model,
                )
                _seed_schedules(car)
                messages.success(request, f'"{nickname}" added to your garage.')

        elif action == 'delete_car':
            car = get_object_or_404(Vehicle, id=request.POST.get('car_id'), owner=request.user)
            car.delete()
            messages.success(request, 'Car removed from your garage.')

        elif action == 'update_mileage':
            car = get_object_or_404(Vehicle, id=request.POST.get('car_id'), owner=request.user)
            car.mileage         = max(int(request.POST.get('mileage', 0)), car.mileage)
            car.battery_percent = min(max(int(request.POST.get('battery_percent', 100)), 0), 100)
            car.save()
            messages.success(request, 'Vehicle updated.')

        elif action == 'update_component':
            car = get_object_or_404(Vehicle, id=request.POST.get('car_id'), owner=request.user)
            messages.success(request, 'Component status noted.')

        return redirect('dashboard:vehicle')

    cars = Vehicle.objects.filter(owner=request.user)
    selected_id  = request.GET.get('car')
    selected_car = cars.filter(id=selected_id).first() if selected_id else None
    if not selected_car and cars.exists():
        selected_car = cars.first()

    return render(request, 'vehicle.html', {
        'cars':         cars,
        'car_count':    cars.count(),
        'selected_car': selected_car,
    })


# ── Maintenance ────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def maintenance(request, vehicle_id):
    car = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_interval':
            schedule_id    = request.POST.get('schedule_id')
            interval_km    = request.POST.get('interval_km')
            interval_months = request.POST.get('interval_months')
            sched = get_object_or_404(ServiceSchedule, id=schedule_id, vehicle=car)
            if interval_km:    sched.interval_km     = int(interval_km)
            if interval_months: sched.interval_months = int(interval_months)
            sched.compute_next_due()
            sched.save()
            messages.success(request, f'{sched.get_component_display()} interval updated.')

        elif action == 'toggle_schedule':
            sched = get_object_or_404(ServiceSchedule, id=request.POST.get('schedule_id'), vehicle=car)
            sched.is_active = not sched.is_active
            sched.save()
            messages.success(request, f'{sched.get_component_display()} {"enabled" if sched.is_active else "disabled"}.')

        return redirect('dashboard:maintenance', vehicle_id=vehicle_id)

    schedules = car.schedules.all()

    # Ensure all 5 default schedules exist
    _seed_schedules(car)
    schedules = car.schedules.all()

    recent_logs = car.logs.all()[:5]

    return render(request, 'maintenance.html', {
        'car':         car,
        'schedules':   schedules,
        'recent_logs': recent_logs,
        'cars':        Vehicle.objects.filter(owner=request.user),
    })


@login_required(login_url='/login/')
def log_service(request, vehicle_id):
    car = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)

    if request.method == 'POST':
        component    = request.POST.get('component', '').strip()
        description  = request.POST.get('description', '').strip()
        odometer     = request.POST.get('odometer', '0')
        service_date = request.POST.get('service_date', '')
        cost         = request.POST.get('cost', '0')
        notes        = request.POST.get('notes', '').strip()

        if not component:
            messages.error(request, 'Please select a component.')
            return redirect('dashboard:log_service', vehicle_id=vehicle_id)

        try:
            parsed_date = date.fromisoformat(service_date) if service_date else date.today()
        except ValueError:
            parsed_date = date.today()

        odometer_val = max(int(odometer), 0)

        # Get matching schedule if exists
        sched = car.schedules.filter(component=component).first()

        log = MaintenanceLog.objects.create(
            vehicle      = car,
            schedule     = sched,
            component    = component,
            description  = description,
            odometer     = odometer_val,
            service_date = parsed_date,
            cost         = float(cost) if cost else 0,
            notes        = notes,
        )

        # Update vehicle mileage if higher
        if odometer_val > car.mileage:
            car.mileage = odometer_val
            car.save()

        # Update schedule's last service info
        if sched:
            sched.last_service_km   = odometer_val
            sched.last_service_date = parsed_date
            sched.compute_next_due()
            sched.save()

        messages.success(request, f'Service logged for {component}.')
        return redirect('dashboard:maintenance', vehicle_id=vehicle_id)

    schedules = car.schedules.filter(is_active=True)
    return render(request, 'log_service.html', {
        'car':       car,
        'schedules': schedules,
        'today':     date.today().isoformat(),
        'cars':      Vehicle.objects.filter(owner=request.user),
    })


@login_required(login_url='/login/')
def service_history(request, vehicle_id):
    car  = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)
    logs = car.logs.all()
    return render(request, 'service_history.html', {
        'car':  car,
        'logs': logs,
        'cars': Vehicle.objects.filter(owner=request.user),
    })


# ── Location ───────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def location(request):
    return render(request, 'location.html')


# ── Upgrade ────────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def upgrade(request):
    cars = Vehicle.objects.filter(owner=request.user)
    selected_id  = request.GET.get('car')
    selected_car = cars.filter(id=selected_id).first() if selected_id else None
    if not selected_car and cars.exists():
        selected_car = cars.first()

    red_schedules    = []
    yellow_schedules = []

    if selected_car:
        schedules = ServiceSchedule.objects.filter(vehicle=selected_car, is_active=True)
        red_schedules    = [s for s in schedules if s.alert_level == 'red']
        yellow_schedules = [s for s in schedules if s.alert_level == 'yellow']

    return render(request, 'upgrade.html', {
        'cars':             cars,
        'selected_car':     selected_car,
        'red_schedules':    red_schedules,
        'yellow_schedules': yellow_schedules,
    })


# ── Profile ────────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def profile(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_info':
            new_username = request.POST.get('username', '').strip()
            new_email    = request.POST.get('email', '').strip().lower()
            if new_username and new_username != request.user.username:
                if User.objects.filter(username__iexact=new_username).exclude(pk=request.user.pk).exists():
                    messages.error(request, 'That username is already taken.')
                else:
                    request.user.username = new_username
                    request.user.save()
                    messages.success(request, 'Username updated.')
            if new_email and new_email != request.user.email:
                if User.objects.filter(email__iexact=new_email).exclude(pk=request.user.pk).exists():
                    messages.error(request, 'That email is already in use.')
                else:
                    request.user.email = new_email
                    request.user.save()
                    messages.success(request, 'Email updated.')

        elif action == 'change_password':
            current = request.POST.get('current_password', '')
            new_pw  = request.POST.get('new_password', '')
            confirm = request.POST.get('confirm_password', '')
            if not request.user.check_password(current):
                messages.error(request, 'Current password is incorrect.')
            elif len(new_pw) < 8:
                messages.error(request, 'New password must be at least 8 characters.')
            elif new_pw != confirm:
                messages.error(request, 'New passwords do not match.')
            else:
                request.user.set_password(new_pw)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully.')

        return redirect('dashboard:profile')

    return render(request, 'profile.html')

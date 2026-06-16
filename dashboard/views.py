from datetime import date, timedelta
import sched
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect, get_object_or_404

from ev_data.models import Vehicle, ServiceSchedule, MaintenanceLog,Notification
import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404


# Default schedules applied when a new vehicle is added
MAINTENANCE_RULES = {
    "EMAS 5": {
        "battery": {"check_km": 20000, "check_months": 12, "replace_km": 160000, "replace_months": 96},
        "coolant": {"check_km": 20000, "check_months": 12, "replace_km": 80000, "replace_months": 60},
        "gear_oil": {"check_km": 20000, "check_months": 12, "replace_km": 60000, "replace_months": 60},
        "brake": {"check_km": 20000, "check_months": 12, "replace_km": 40000, "replace_months": 24},
        "tyre": {"check_km": 10000, "check_months": 6, "replace_km": 50000, "replace_months": 48},
    },

    "EMAS 7": {
        "battery": {"check_km": 20000, "check_months": 12, "replace_km": 160000, "replace_months": 96},
        "coolant": {"check_km": 20000, "check_months": 12, "replace_km": 80000, "replace_months": 60},
        "gear_oil": {"check_km": 20000, "check_months": 12, "replace_km": 40000, "replace_months": 48},
        "brake": {"check_km": 20000, "check_months": 12, "replace_km": 40000, "replace_months": 24},
        "tyre": {"check_km": 10000, "check_months": 6, "replace_km": 50000, "replace_months": 48},
    },

    "EMAS PHEV": {
        "battery": {"check_km": 15000, "check_months": 12, "replace_km": 160000, "replace_months": 96},
        "coolant": {"check_km": 15000, "check_months": 12, "replace_km": 60000, "replace_months": 60},
        "gear_oil": {"check_km": 15000, "check_months": 12, "replace_km": 60000, "replace_months": 60},
        "brake": {"check_km": 15000, "check_months": 12, "replace_km": 30000, "replace_months": 24},
        "tyre": {"check_km": 10000, "check_months": 6, "replace_km": 50000, "replace_months": 48},
    }
}

COMPONENT_UI = {
    "coolant": {"label": "Coolant Fluid", "img": "image/coolant.png", "hotspot": "eh-1"},
    "brake": {"label": "Brake Fluid", "img": "image/brakefluid.png", "hotspot": "eh-2"},
    "battery": {"label": "Battery", "img": "image/battery.avif", "hotspot": "eh-3"},
    "gear_oil": {"label": "Gear Oil", "img": "image/gear.jpg", "hotspot": "eh-4"},
    "tyre": {"label": "Tyre", "img": "image/tyreemas5.png", "hotspot": "tyre"},
}

def _seed_schedules(vehicle):
    rules = MAINTENANCE_RULES.get(vehicle.model)
    if not rules:
        return

    for component, rule in rules.items():
        sched, created = ServiceSchedule.objects.get_or_create(
            vehicle=vehicle,
            component=component,
            defaults={
                "interval_km": rule["check_km"],
                "interval_months": rule["check_months"],
                "last_service_km": 0,
                "last_service_date": None,
                "last_checked_km": 0,
                "last_checked_date": None,
            }
        )

        if created:
            sched.last_service_km = 0
            sched.last_service_date = None
            sched.last_checked_km = 0
            sched.last_checked_date = None

        sched.compute_next_due()
        sched.save()
        
def compute_status_percent(schedule, vehicle):
    if not schedule.next_due_km:
        return 100

    used = vehicle.mileage - schedule.last_service_km
    if schedule.interval_km == 0:
        return 100

    percent = 100 - (used / schedule.interval_km) * 100

    return max(0, min(100, int(percent)))

def calc_status_percent(car, sched, rule):
    if getattr(sched, "is_reset", False):
        return 100

    today = date.today()

    km_used = car.mileage - (sched.last_service_km or 0)
    km_ratio = km_used / max(rule["replace_km"], 1)
    mileage_percent = max(0, min(100, int(100 * (1 - km_ratio))))

    if sched.last_service_date:
        age_months = (today - sched.last_service_date).days // 30
    else:
        age_months = (today.year - car.year) * 12

    time_ratio = age_months / max(rule["replace_months"], 1)
    time_percent = max(0, min(100, int(100 * (1 - time_ratio))))

    return (mileage_percent + time_percent) // 2

def get_component_status(car, sched, rule):

    if getattr(sched, "is_reset", False):
        return 100

    today = date.today()

    # ===== CHECK BASE LINE =====
    base_km = sched.last_service_km or 0
    base_date = sched.last_service_date

    # ================= KM =================
    km_used = max(car.mileage - base_km, 0)
    mileage_percent = 100 - (km_used / max(rule["replace_km"], 1)) * 100

    # ================= TIME =================
    if base_date:
        age_months = (today - base_date).days // 30
    else:
        age_months = (today.year - car.year) * 12

    time_percent = 100 - (age_months / max(rule["replace_months"], 1)) * 100

    final = (mileage_percent + time_percent) / 2

    return max(0, min(100, int(final)))

def generate_notifications(user):

    Notification.objects.filter(
        user=user,
        notification_type="maintenance"
    ).delete()

    cars = Vehicle.objects.filter(owner=user)

    if not user or not user.is_authenticated:
        return

    for car in cars:
        schedules = ServiceSchedule.objects.filter(vehicle=car, is_active=True)
        rules = MAINTENANCE_RULES.get(car.model, {})

        for sched in schedules:
            rule = rules.get(sched.component)
            if not rule:
                continue

            comp_label = COMPONENT_UI.get(sched.component, {}).get("label", sched.component)

            percent = get_component_status(car, sched, rule)

            # ================= URGENT =================
            if percent <= 24:
                Notification.objects.get_or_create(
                    user=user,
                    vehicle=car,
                    component=sched.component,
                    cycle_marker=f"{car.id}-{sched.component}",
                    defaults={
                        "notification_type": "maintenance",
                        "level": "urgent",
                        "is_read": False,
                        "message" : f"{car.nickname} ({car.model}) - {comp_label} is CRITICAL ({percent}%) - Please do replacement."
                    }
                )

            # ================= CHECK =================
            else:

                base_km = sched.last_checked_km or sched.last_service_km or 0
                km_used = car.mileage - base_km
                mileage_due = km_used >= rule["check_km"]

                if sched.last_checked_date:
                    months_used = (date.today() - sched.last_checked_date).days // 30
                else:
                    months_used = 999

                time_due = months_used >= rule["check_months"]

                if mileage_due or time_due:

                    Notification.objects.get_or_create(
                        user=user,
                        vehicle=car,
                        component=sched.component,
                        cycle_marker=f"{car.id}-{sched.component}",
                        defaults={
                            "notification_type": "maintenance",
                            "level": "normal",
                            "is_read": False,
                            "message" : f"{car.nickname} ({car.model}) - {comp_label} needs CHECK inspection. Please check condition."
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

        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')

        unread_count = notifications.filter(is_read=False).count()

        context["notifications"] = notifications[:10]
        context["unread_count"] = unread_count

    return render(request, 'Home.html', context)


# ── Vehicle ────────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def export_all_cars_components(request):

    cars = Vehicle.objects.filter(owner=request.user)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="all_cars_components.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "Car ID",
        "Nickname",
        "Model",
        "Component",
        "Mileage",
        "Last Service KM",
        "Last Service Date",
        "Next Due KM",
        "Next Due Date",
        "Status %"
    ])

    for car in cars:

        schedules = ServiceSchedule.objects.filter(
            vehicle=car,
            is_active=True
        )

        rules = MAINTENANCE_RULES.get(car.model, {})

        for s in schedules:

            rule = rules.get(s.component)
            if not rule:
                continue

            # ===== REAL CALCULATION =====
            km_used = car.mileage - (s.last_service_km or 0)
            km_percent = 100 - int((km_used / rule["replace_km"]) * 100)

            if s.last_service_date:
                age_months = (date.today() - s.last_service_date).days // 30
            else:
                age_months = 0

            time_percent = 100 - int((age_months / rule["replace_months"]) * 100)

            status_percent = max(0, min(100, (km_percent + time_percent) // 2))

            writer.writerow([
                car.id,
                car.nickname,
                car.model,
                s.component,
                car.mileage,
                s.last_service_km,
                s.last_service_date,
                s.next_due_km,
                s.next_due_date,
                status_percent
            ])

    return response
    
@login_required(login_url='/login/')
def vehicle(request):

    Notification.objects.filter(user=request.user).delete()
    generate_notifications(request.user)

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

        elif action == "delete_car":
            ids = request.POST.getlist("delete_ids")
            Vehicle.objects.filter(
                id__in=ids,
                owner=request.user
            ).delete()

        elif action == 'update_mileage':
            car = get_object_or_404(
                Vehicle,
                id=request.POST.get('car_id'),
                owner=request.user
            )
            added_mileage = int(request.POST.get('mileage', 0))
            car.mileage += max(added_mileage, 0)
            car.battery_percent = min(
                max(int(request.POST.get('battery_percent', 100)), 0),
                100
            )
            car.updated_at = timezone.now()
            car.save()

        elif action == 'update_component':

            car = get_object_or_404(
                Vehicle,
                id=request.POST.get('car_id'),
                owner=request.user
            )


            COMPONENTS = ["tyre", "brake", "coolant", "battery", "gear_oil"]

            for component in COMPONENTS:

                status = request.POST.get(component)  # ⭐ replacement / checking / none

                if not status:
                    continue

                sched = ServiceSchedule.objects.filter(
                    vehicle=car,
                    component=component
                ).first()

                if not sched:
                    continue

                # =========================
                # 🔥 CORE LOGIC
                # =========================
                
                if status == "replacement":
                    sched.last_service_km = car.mileage
                    sched.last_service_date = date.today()

                    sched.last_checked_km = car.mileage
                    sched.last_checked_date = date.today()


                elif status == "checking":
                    sched.last_checked_km = car.mileage
                    sched.last_checked_date = date.today()
                    sched.is_reset = False

                elif status == "none":
                    pass

                else:
                    sched.is_reset = False

                sched.compute_next_due()
                sched.save()

                Notification.objects.filter(
                    user=request.user,
                    vehicle=car,
                    component=component,
                    s_resolved=False
                ).update(s_resolved=True)


        return redirect('dashboard:vehicle')

    cars = Vehicle.objects.filter(owner=request.user)

    selected_id = request.GET.get("car")

    if selected_id:
        selected_car = cars.filter(id=selected_id).first()
    else:
        selected_car = cars.first() if cars.exists() else None

    if not selected_car:
        return render(request, "vehicle.html", {
            "cars": cars,
            "car_count": cars.count(),
            "selected_car": None,
            "components": {},
            "full_range": None,
            "estimate_range": None,
        })

    # attach images for all cars
    for car in cars:
        car.image = car.get_image()
        car.engine_image = car.get_engine_image()

    # AFTER selected_car is finalized
    components_qs = ServiceSchedule.objects.filter(
        vehicle=selected_car,
        is_active=True
    ) if selected_car else ServiceSchedule.objects.none()

    if selected_car:
        rules = MAINTENANCE_RULES.get(selected_car.model, {})
    else:
        rules = {}

    today = date.today()
    age_months = max(0, (today.year - selected_car.year) * 12)

    components = {}
    for c in components_qs:

        config = COMPONENT_UI.get(c.component, {})
        rule = rules.get(c.component)

        if not rule:
            continue

        # ⭐ RESET OVERRIDE
        if getattr(c, "is_reset", False):
            mileage_percent = 100
            time_percent = 100
            final_percent = 100
            
        else:
            km_used = selected_car.mileage - (c.last_service_km or 0)

            mileage_percent = max(0, min(100,
                int(100 * (1 - km_used / max(rule["replace_km"], 1)))
            ))

            time_ratio = age_months / max(rule["replace_months"], 1)
            time_percent = max(0, min(100, int(100 * (1 - time_ratio))))

            final_percent = get_component_status(selected_car, c, rule)


        c.status_percent = final_percent
        c.save(update_fields=["status_percent"])

        components[c.component] = {
            "label": config.get("label", c.component),
            "img": config.get("img", "image/default.png"),
            "hotspot": config.get("hotspot", c.component),

            "mileage_percent": mileage_percent,
            "time_percent": time_percent,
            "status_percent": final_percent,
        }

    for key, config in COMPONENT_UI.items():
        if key not in components:
            components[key] = {
                "label": config["label"],
                "img": config["img"],
                "hotspot": config["hotspot"],
                "status_percent": 100,
                "mileage_percent": 100,
                "time_percent": 100,
            }

    # now safe to attach images
    if selected_car:
        selected_car.image = selected_car.get_image()
        selected_car.engine_image = selected_car.get_engine_image()

        RANGE_MAP = {
            "EMAS 5": 325,
            "EMAS 7": 410,
            "EMAS PHEV": 996,
        }

        full_range = RANGE_MAP.get(selected_car.model, 0)

        estimate_range = round(
            full_range * selected_car.battery_percent / 100
        )

        all_schedules = ServiceSchedule.objects.filter(
        vehicle=selected_car,
        is_active=True
    )
        
        generate_notifications(request.user)

        for s in all_schedules:
            percent = compute_status_percent(s, selected_car)

    else:
        full_range = None
        estimate_range = None

    notifications = Notification.objects.filter(
    user=request.user
    ).order_by("-created_at")

    return render(request, 'vehicle.html', {
        'cars': cars,
        'car_count': cars.count(),
        'selected_car': selected_car,
        'full_range': full_range,
        'estimate_range': estimate_range,
        'components': components,
        'notifications': notifications,
    })

@login_required(login_url='/login/')
def mark_notifications_read(request):
    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    return redirect(request.META.get('HTTP_REFERER', 'dashboard:vehicle'))

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

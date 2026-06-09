from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import estimate_charging_time_minutes, estimate_remaining_range_km


@login_required
def calculator_view(request):
    result = None

    if request.method == "POST":
        result = {
            "remaining_range_km": estimate_remaining_range_km(
                request.POST.get("battery_capacity_kwh"),
                request.POST.get("current_battery_percent"),
                request.POST.get("kwh_per_100km"),
            ),
            "charging_time_minutes": estimate_charging_time_minutes(
                request.POST.get("battery_capacity_kwh"),
                request.POST.get("battery_start_percent"),
                request.POST.get("battery_target_percent"),
                request.POST.get("charger_power_kw"),
            ),
        }

    return render(request, "ev_calculation/calculator.html", {"result": result})
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def to_decimal(value, default=None):
    try:
        if value is None or value == "":
            return default

        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def round_decimal(value, places=2):
    if value is None:
        return None

    quantize_value = Decimal("1." + ("0" * places))

    return Decimal(value).quantize(quantize_value, rounding=ROUND_HALF_UP)


def calculate_distance_km(start_odometer, end_odometer):
    start = to_decimal(start_odometer)
    end = to_decimal(end_odometer)

    if start is None or end is None:
        return None

    distance = end - start

    if distance <= 0:
        return None

    return distance


def calculate_battery_added_percent(battery_start_percent, battery_end_percent):
    start = to_decimal(battery_start_percent)
    end = to_decimal(battery_end_percent)

    if start is None or end is None:
        return None

    if start < 0 or end > 100 or end <= start:
        return None

    return end - start


def calculate_energy_from_battery_percent(
    battery_capacity_kwh,
    battery_start_percent,
    battery_end_percent,
):
    battery_added_percent = calculate_battery_added_percent(
        battery_start_percent,
        battery_end_percent,
    )

    capacity = to_decimal(battery_capacity_kwh)

    if capacity is None or battery_added_percent is None:
        return None

    energy_added = capacity * (battery_added_percent / Decimal("100"))

    return round_decimal(energy_added, 2)


def calculate_kwh_per_100km(energy_added_kwh, distance_km):
    energy = to_decimal(energy_added_kwh)
    distance = to_decimal(distance_km)

    if energy is None or distance is None or distance <= 0:
        return None

    efficiency = (energy / distance) * Decimal("100")

    return round_decimal(efficiency, 2)


def calculate_cost_per_km(cost, distance_km):
    amount = to_decimal(cost)
    distance = to_decimal(distance_km)

    if amount is None or distance is None or distance <= 0:
        return None

    return round_decimal(amount / distance, 2)


def calculate_cost_per_100km(cost, distance_km):
    amount = to_decimal(cost)
    distance = to_decimal(distance_km)

    if amount is None or distance is None or distance <= 0:
        return None

    return round_decimal((amount / distance) * Decimal("100"), 2)


def calculate_charging_cost(energy_added_kwh, price_per_kwh, parking_fee=0):
    energy = to_decimal(energy_added_kwh)
    price = to_decimal(price_per_kwh)
    parking = to_decimal(parking_fee, Decimal("0"))

    if energy is None or price is None:
        return None

    total_cost = (energy * price) + parking

    return round_decimal(total_cost, 2)


def estimate_range_km(battery_capacity_kwh, kwh_per_100km):
    capacity = to_decimal(battery_capacity_kwh)
    efficiency = to_decimal(kwh_per_100km)

    if capacity is None or efficiency is None or efficiency <= 0:
        return None

    estimated_range = (capacity / efficiency) * Decimal("100")

    return round_decimal(estimated_range, 0)


def estimate_remaining_range_km(
    battery_capacity_kwh,
    current_battery_percent,
    kwh_per_100km,
):
    capacity = to_decimal(battery_capacity_kwh)
    battery_percent = to_decimal(current_battery_percent)
    efficiency = to_decimal(kwh_per_100km)

    if (
        capacity is None
        or battery_percent is None
        or efficiency is None
        or battery_percent < 0
        or battery_percent > 100
        or efficiency <= 0
    ):
        return None

    usable_energy = capacity * (battery_percent / Decimal("100"))
    remaining_range = (usable_energy / efficiency) * Decimal("100")

    return round_decimal(remaining_range, 0)


def estimate_charging_time_minutes(
    battery_capacity_kwh,
    battery_start_percent,
    battery_target_percent,
    charger_power_kw,
):
    capacity = to_decimal(battery_capacity_kwh)
    start = to_decimal(battery_start_percent)
    target = to_decimal(battery_target_percent)
    power = to_decimal(charger_power_kw)

    if (
        capacity is None
        or start is None
        or target is None
        or power is None
        or start < 0
        or target > 100
        or target <= start
        or power <= 0
    ):
        return None

    energy_needed = capacity * ((target - start) / Decimal("100"))
    hours_needed = energy_needed / power
    minutes_needed = hours_needed * Decimal("60")

    return round_decimal(minutes_needed, 0)


def summarize_charging_session(
    previous_odometer,
    current_odometer,
    energy_added_kwh,
    charging_cost,
    battery_capacity_kwh=None,
    battery_start_percent=None,
    battery_end_percent=None,
):
    distance_km = calculate_distance_km(previous_odometer, current_odometer)

    energy = to_decimal(energy_added_kwh)

    if energy is None and battery_capacity_kwh is not None:
        energy = calculate_energy_from_battery_percent(
            battery_capacity_kwh=battery_capacity_kwh,
            battery_start_percent=battery_start_percent,
            battery_end_percent=battery_end_percent,
        )

    return {
        "distance_km": round_decimal(distance_km, 0),
        "energy_added_kwh": round_decimal(energy, 2),
        "battery_added_percent": calculate_battery_added_percent(
            battery_start_percent,
            battery_end_percent,
        ),
        "kwh_per_100km": calculate_kwh_per_100km(energy, distance_km),
        "cost_per_km": calculate_cost_per_km(charging_cost, distance_km),
        "cost_per_100km": calculate_cost_per_100km(charging_cost, distance_km),
    }

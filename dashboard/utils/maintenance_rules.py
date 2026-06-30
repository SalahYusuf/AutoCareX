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


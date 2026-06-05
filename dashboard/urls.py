from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('',                                    views.home,             name='index'),
    path('vehicle/',                            views.vehicle,          name='vehicle'),
    path('location/',                           views.location,         name='location'),
    path('upgrade/',                            views.upgrade,          name='upgrade'),
    path('profile/',                            views.profile,          name='profile'),

    # Maintenance
    path('maintenance/<int:vehicle_id>/',       views.maintenance,      name='maintenance'),
    path('maintenance/<int:vehicle_id>/log/',   views.log_service,      name='log_service'),
    path('maintenance/<int:vehicle_id>/history/', views.service_history, name='service_history'),
]

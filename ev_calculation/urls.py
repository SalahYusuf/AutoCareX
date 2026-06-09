from django.urls import path
from . import views

app_name = "ev_calculation"

urlpatterns = [
    path("", views.calculator_view, name="calculator"),
]
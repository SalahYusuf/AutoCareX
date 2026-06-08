from django.urls import path

from . import views

app_name = "login"

urlpatterns = [
    path("",                          views.login_view,       name="login"),
    path("signup/",                   views.signup_view,      name="signup"),
    path("verify-email/<str:token>/", views.verify_email_view, name="verify_email"),
    path("logout/",                   views.logout_view,      name="logout"),
]

urlpatterns = [
    path('location/', views.location_view, name='location'),
]

from django.urls import path

from . import views

app_name = "login"

urlpatterns = [
    path("",                          views.login_view,       name="login"),
    path("signup/",                   views.signup_view,      name="signup"),
    path("verify-email/<str:token>/", views.verify_email_view, name="verify_email"),
    path("forgot-password/",           views.forgot_password_view, name="forgot_password"),
    path("reset-password/<uidb64>/<token>/", views.reset_password_view, name="reset_password"),
    path("logout/",                   views.logout_view,      name="logout"),
]

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.shortcuts import get_object_or_404, redirect, render

from .models import EmailVerificationToken


# ── Sign Up ────────────────────────────────────────────────────────────────────

def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email    = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        if not all([username, email, password]):
            messages.error(request, "All fields are required.")
            return render(request, "login/signup.html")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "login/signup.html")

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "That username is already taken.")
            return render(request, "login/signup.html")

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "An account with that email already exists.")
            return render(request, "login/signup.html")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        user.is_active = False
        user.save()

        token_obj = EmailVerificationToken.create_for_user(user)
        verify_url = f"{settings.SITE_URL}/login/verify-email/{token_obj.token}/"

        if settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
            print(f"\nAutoCareX verification link for {email}: {verify_url}\n")

        try:
            send_mail(
                subject="Verify your AutoCareX account",
                message=(
                    f"Hi {username},\n\n"
                    f"Click the link below to verify your account:\n\n"
                    f"{verify_url}\n\n"
                    f"This link expires in 24 hours.\n\n"
                    f"— The AutoCareX Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception:
            # Keep the database clean if email delivery fails, so the user can retry signup.
            user.delete()
            messages.error(
                request,
                "Account was not created because the verification email could not be sent. "
                "Check your email settings or use the terminal verification link in local testing.",
            )
            return render(request, "login/signup.html")

        messages.success(request, "Account created! Check your email to verify.")
        return redirect("login:login")

    return render(request, "login/signup.html")

# ── Email Verification ─────────────────────────────────────────────────────────

def verify_email_view(request, token):
    token_obj = get_object_or_404(EmailVerificationToken, token=token)

    if not token_obj.is_valid():
        token_obj.delete()
        messages.error(request, "This verification link has expired. Please sign up again.")
        return redirect("login:signup")

    user = token_obj.user
    user.is_active = True
    user.save()
    token_obj.delete()

    messages.success(request, "Email verified! You can now log in.")
    return redirect("login:login")


# ── Login ──────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()  # username or email
        password   = request.POST.get("password", "")

        if not identifier or not password:
            messages.error(request, "Please fill in all fields.")
            return render(request, "login/login.html")

        # Allow login with either username or email
        user = None

        # Try username first
        user = authenticate(request, username=identifier, password=password)

        # If that failed, try looking up by email
        if user is None:
            try:
                matched = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=matched.username, password=password)
            except User.DoesNotExist:
                pass

        if user is None:
            messages.error(request, "Invalid username/email or password.")
            return render(request, "login/login.html")

        if not user.is_active:
            messages.error(request, "Please verify your email before logging in.")
            return render(request, "login/login.html")

        auth_login(request, user)
        next_url = request.POST.get("next") or request.GET.get("next") or "dashboard:index"
        return redirect(next_url)

    return render(request, "login/login.html")


# ── Forgot Password ────────────────────────────────────────────────────────────

def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "Please enter your email address.")
            return render(request, "login/forgot_password_email.html")

        user = User.objects.filter(email__iexact=email).first()

        if user:
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_path = reverse("login:reset_password", kwargs={"uidb64": uidb64, "token": token})
            reset_url = f"{settings.SITE_URL}{reset_path}"

            if settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
                print(f"\nAutoCareX password reset link for {email}: {reset_url}\n")

            try:
                send_mail(
                    subject="Reset your AutoCareX password",
                    message=(
                        f"Hi {user.username},\n\n"
                        f"Click the link below to reset your AutoCareX password:\n\n"
                        f"{reset_url}\n\n"
                        f"If you did not request this, you can ignore this email.\n\n"
                        f"— The AutoCareX Team"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception:
                messages.error(request, "The reset email could not be sent. Please try again later.")
                return render(request, "login/forgot_password_email.html")

        messages.success(request, "If the email exists, a password reset link has been sent.")
        return redirect("login:login")

    return render(request, "login/forgot_password_email.html")


def reset_password_view(request, uidb64, token):
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    user = None

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "This password reset link is invalid or has expired.")
        return redirect("login:forgot_password")

    if request.method == "POST":
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        if not password1 or not password2:
            messages.error(request, "Please fill in both password fields.")
            return render(request, "login/forgotpassword_reset.html")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "login/forgotpassword_reset.html")

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "login/forgotpassword_reset.html")

        user.set_password(password1)
        user.save()

        messages.success(request, "Your password has been reset. You can now log in.")
        return redirect("login:login")

    return render(request, "login/forgotpassword_reset.html")


# ── Logout ─────────────────────────────────────────────────────────────────────

def logout_view(request):
    auth_logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("dashboard:index")



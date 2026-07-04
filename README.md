# AutoCareX

AutoCareX is a Django-based web application for Proton e.MAS users. It allows users to register an account, verify their email, manage their vehicles, track maintenance, update mileage and battery status, view service history, and manage their profile.

## Live Demo

PythonAnywhere deployment:

https://salahyusuf.pythonanywhere.com

Note: The final tested version of this project was verified locally using Django `runserver`. The PythonAnywhere deployment is provided as an online demo.

## Main Features

- User registration
- Email verification
- User login and logout
- Forgot password and reset password
- Profile page
- Change password
- Delete account
- Vehicle registration
- Vehicle list and selected vehicle view
- Mileage update
- Battery percentage update
- Maintenance tracking
- Service logging
- Service history
- Car workshop page
- Contact page
- Shared navbar and footer
- Page transition effects

## Technologies Used

- Python
- Django
- HTML
- CSS
- JavaScript
- SQLite
- Gmail SMTP

## Project Structure

```text
AutoCareX/
├── core/
├── dashboard/
├── login/
├── static/
├── templates/
├── media/
├── manage.py
├── requirements.txt
└── README.md

1. Clone the project
git clone https://github.com/SalahYusuf/AutoCareX.git
cd AutoCareX

2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

for windows:
python -m venv .venv
.venv/Scripts/activate

3. Install requirements
pip install -r requirements.txt

4. create .env file
MAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True

EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_google_app_password
DEFAULT_FROM_EMAIL=your_email@gmail.com

SITE_URL=http://127.0.0.1:8000

5. run server
python3 manage.py migrate
python3 manage.py runserver


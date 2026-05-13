import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HospitalManagementSystem.settings')
django.setup()

from django.contrib.auth.models import User

# Set email for admin user
u = User.objects.filter(username='admin').first()
if u:
    u.email = 'admin@hospital.com'
    u.save()
    print(f'Admin user email set to: {u.email}')
    print(f'Username: {u.username}')
else:
    print('Admin user not found')

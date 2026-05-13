import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HospitalManagementSystem.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

# Reset password for admin user
u = User.objects.filter(username='admin').first()
if u:
    u.set_password('admin123')
    u.save()
    print('Password reset for admin user')
    print(f'Check password: {u.check_password("admin123")}')
    
    # Test authenticate
    user = authenticate(username='admin', password='admin123')
    print(f'Authenticate result: {user}')
    if user:
        print(f'User is staff: {user.is_staff}')


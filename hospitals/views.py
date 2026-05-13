from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from .models import *
from datetime import date
import json

# Create your views here.

def About(request):
    return render(request,'about.html')

def Index(request):
    return render(request,'index.html')

def contact(request):
    error = ""
    if request.method == 'POST':
        n = request.POST['name']
        c = request.POST['contact']
        e = request.POST['email']
        s = request.POST['subject']
        m = request.POST['message']
        try:
            Contact.objects.create(name=n, contact=c, email=e, subject=s, message=m, msgdate=date.today(), isread="no")
            error = "no"
        except:
            error = "yes"
    return render(request, 'contact.html', locals())

def adminlogin(request):
    error = ""
    if request.method == 'POST':
        u = request.POST['uname']
        p = request.POST['pwd']
        user = authenticate(username=u, password=p)
        if user is None:
            user_obj = User.objects.filter(email__iexact=u).first()
            if user_obj:
                user = authenticate(username=user_obj.username, password=p)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('admin_home')
        error = "yes"
    return render(request,'login.html', locals())

def forgot_password(request):
    message = ""
    message_type = ""
    if request.method == 'POST':
        username_or_email = request.POST.get('username_or_email', '')
        try:
            user = User.objects.filter(username=username_or_email).first() or User.objects.filter(email=username_or_email).first()
            if user:
                # Generate reset token
                token = default_token_generator.make_token(user)
                reset_link = request.build_absolute_uri(reverse('reset_password', args=[user.pk, token]))
                
                # Try to send email
                try:
                    send_mail(
                        'HMS - Password Reset',
                        f'Click the link to reset your password: {reset_link}',
                        'noreply@hospitalms.com',
                        [user.email or 'admin@hospital.com'],
                        fail_silently=False,
                    )
                    message = "Password reset link has been sent to your email!"
                    message_type = "success"
                except Exception as e:
                    # Email not configured, show manual reset option
                    message = f"Please contact the admin with username '{user.username}' to reset your password."
                    message_type = "info"
            else:
                message = "No account found with that username or email."
                message_type = "error"
        except Exception as e:
            message = "An error occurred. Please try again later."
            message_type = "error"
    
    return render(request, 'forgot_password.html', {'message': message, 'message_type': message_type})

def reset_password(request, uid, token):
    try:
        user = User.objects.get(pk=uid)
        if default_token_generator.check_token(user, token):
            if request.method == 'POST':
                new_password = request.POST.get('new_password', '')
                confirm_password = request.POST.get('confirm_password', '')
                if new_password == confirm_password and len(new_password) >= 6:
                    user.set_password(new_password)
                    user.save()
                    return redirect('login')
                else:
                    error = "Passwords do not match or are too short!"
                    return render(request, 'reset_password.html', {'error': error, 'uid': uid, 'token': token})
            return render(request, 'reset_password.html', {'uid': uid, 'token': token})
        else:
            return redirect('login')
    except User.DoesNotExist:
        return redirect('login')


def signup(request):
    error = ""
    if request.method == 'POST':
        u = request.POST['uname']
        p = request.POST['pwd']
        cp = request.POST['cpwd']
        if p != cp:
            error = "mismatch"
        elif User.objects.filter(username=u).exists():
            error = "exists"
        else:
            try:
                User.objects.create_user(username=u, password=p, is_staff=True)
                error = "no"
            except:
                error = "yes"
    return render(request, 'signup.html', locals())


def admin_home(request):
    if not request.user.is_staff:
        return redirect('login')

    today = date.today()
    dc = Doctor.objects.count()
    pc = Patient.objects.count()
    ac = Appointment.objects.count()
    dept = Doctor.objects.values_list('special', flat=True).distinct().count()
    today_appointments = Appointment.objects.filter(date1=today).count()

    upcoming_qs = Appointment.objects.order_by('date1', 'time1')[:5]
    upcoming_appointments = []
    for appointment in upcoming_qs:
        upcoming_appointments.append({
            'patient': appointment.patient.name,
            'doctor': appointment.doctor.name,
            'department': appointment.doctor.special,
            'date': appointment.date1,
            'time': appointment.time1,
            'status': 'Confirmed' if appointment.date1 >= today else 'Pending'
        })

    activities = []
    for patient in Patient.objects.order_by('-id')[:2]:
        activities.append({
            'title': f'Patient registered: {patient.name}',
            'subtitle': 'New patient added to the system',
            'time': 'Just now',
            'icon': 'fa-user-plus',
            'badge': 'info'
        })
    for appointment in Appointment.objects.order_by('-date1', '-time1')[:2]:
        activities.append({
            'title': f'Appointment booked for {appointment.patient.name}',
            'subtitle': f'{appointment.doctor.name} • {appointment.doctor.special}',
            'time': appointment.date1.strftime('%b %d'),
            'icon': 'fa-calendar-check-o',
            'badge': 'success'
        })
    for doctor in Doctor.objects.order_by('-id')[:1]:
        activities.append({
            'title': f'Doctor added: {doctor.name}',
            'subtitle': f'Specialty: {doctor.special}',
            'time': '1 hour ago',
            'icon': 'fa-user-md',
            'badge': 'warning'
        })

    month_labels = []
    month_counts = []
    for delta in range(5, -1, -1):
        month_index = today.month - delta
        year = today.year + ((month_index - 1) // 12)
        month = ((month_index - 1) % 12) + 1
        label_date = date(year, month, 1)
        month_labels.append(label_date.strftime('%b'))
        count = Appointment.objects.filter(date1__year=year, date1__month=month).count()
        month_counts.append(count)

    context = {
        'dc': dc,
        'pc': pc,
        'ac': ac,
        'dept': dept,
        'today_appointments': today_appointments,
        'upcoming_appointments': upcoming_appointments,
        'recent_activities': activities,
        'patient_overview_labels': json.dumps(month_labels),
        'patient_overview_counts': json.dumps(month_counts)
    }
    return render(request,'admin_home.html', context)

def Logout(request):
    logout(request)
    return redirect('index')

def add_doctor(request):
    error=""
    if not request.user.is_staff:
        return redirect('login')
    if request.method=='POST':
        n = request.POST['name']
        m = request.POST['mobile']
        sp = request.POST['special']
        try:
            Doctor.objects.create(name=n,mobile=m,special=sp)
            error="no"
        except:
            error="yes"
    return render(request,'add_doctor.html', locals())

def view_doctor(request):
    if not request.user.is_staff:
        return redirect('login')
    doc = Doctor.objects.all()
    d = {'doc':doc}
    return render(request,'view_doctor.html', d)

def Delete_Doctor(request,pid):
    if not request.user.is_staff:
        return redirect('login')
    doctor = Doctor.objects.get(id=pid)
    doctor.delete()
    return redirect('view_doctor')

def edit_doctor(request,pid):
    error = ""
    if not request.user.is_staff:
        return redirect('login')
    doctor = Doctor.objects.get(id=pid)
    if request.method == "POST":
        n1 = request.POST['name']
        m1 = request.POST['mobile']
        s1 = request.POST['special']

        doctor.name = n1
        doctor.mobile = m1
        doctor.special = s1

        try:
            doctor.save()
            error = "no"
        except:
            error = "yes"
    return render(request, 'edit_doctor.html', locals())

def add_patient(request):
    error = ""
    if not request.user.is_staff:
        return redirect('login')
    if request.method == 'POST':
        n = request.POST['name']
        g = request.POST['gender']
        m = request.POST['mobile']
        a = request.POST['address']
        w = request.POST.get('ward', '')
        try:
            Patient.objects.create(name=n, gender=g, mobile=m, address=a, ward=w)
            error = "no"
        except:
            error = "yes"
    return render(request,'add_patient.html', locals())

def view_patient(request):
    if not request.user.is_staff:
        return redirect('login')
    pat = Patient.objects.all()
    d = {'pat':pat}
    return render(request,'view_patient.html', d)

def Delete_Patient(request,pid):
    if not request.user.is_staff:
        return redirect('login')
    patient = Patient.objects.get(id=pid)
    patient.delete()
    return redirect('view_patient')

def edit_patient(request,pid):
    error = ""
    if not request.user.is_authenticated:
        return redirect('login')
    user = request.user
    patient = Patient.objects.get(id=pid)
    if request.method == "POST":
        n1 = request.POST['name']
        m1 = request.POST['mobile']
        g1 = request.POST['gender']
        a1 = request.POST['address']
        w1 = request.POST.get('ward', '')

        patient.name = n1
        patient.mobile = m1
        patient.gender = g1
        patient.address = a1
        patient.ward = w1
        try:
            patient.save()
            error = "no"
        except:
            error = "yes"
    return render(request, 'edit_patient.html', locals())



def add_appointment(request):
    error=""
    if not request.user.is_staff:
        return redirect('login')
    doctor1 = Doctor.objects.all()
    patient1 = Patient.objects.all()
    if request.method=='POST':
        d = request.POST['doctor']
        p = request.POST['patient']
        d1 = request.POST['date']
        t = request.POST['time']
        doctor = Doctor.objects.filter(name=d).first()
        patient = Patient.objects.filter(name=p).first()
        try:
            Appointment.objects.create(doctor=doctor, patient=patient, date1=d1, time1=t)
            error="no"
        except:
            error="yes"
    d = {'doctor':doctor1,'patient':patient1,'error':error}
    return render(request,'add_appointment.html', d)

def view_appointment(request):
    if not request.user.is_staff:
        return redirect('login')
    appointment = Appointment.objects.all()
    d = {'appointment':appointment}
    return render(request,'view_appointment.html', d)

def Delete_Appointment(request,pid):
    if not request.user.is_staff:
        return redirect('login')
    appointment1 = Appointment.objects.get(id=pid)
    appointment1.delete()
    return redirect('view_appointment')

def unread_queries(request):
    if not request.user.is_authenticated:
        return redirect('login')
    contact = Contact.objects.filter(isread="no")
    return render(request,'unread_queries.html', locals())

def read_queries(request):
    if not request.user.is_authenticated:
        return redirect('login')
    contact = Contact.objects.filter(isread="yes")
    return render(request,'read_queries.html', locals())

def view_queries(request,pid):
    if not request.user.is_authenticated:
        return redirect('login')
    contact = Contact.objects.get(id=pid)
    contact.isread = "yes"
    contact.save()
    return render(request,'view_queries.html', locals())


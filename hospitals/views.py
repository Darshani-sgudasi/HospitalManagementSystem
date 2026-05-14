from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import FileResponse, Http404
from django.urls import reverse
from django.utils import timezone
from .models import *
from datetime import date, timedelta
import json
import os

# Create your views here.

FULL_ACCESS_ROLES = ("admin", "doctor")
READ_ONLY_ROLES = ("patient",)
ALL_ROLES = FULL_ACCESS_ROLES + READ_ONLY_ROLES


def selected_role(request):
    role = request.session.get("user_role")
    if not role and request.user.is_authenticated and request.user.is_staff:
        role = "admin"
        request.session["user_role"] = role
    return role


def is_dashboard_user(request):
    return request.user.is_authenticated and selected_role(request) in ALL_ROLES


def can_manage_records(request):
    return request.user.is_authenticated and selected_role(request) in FULL_ACCESS_ROLES


def require_dashboard_access(request):
    if not is_dashboard_user(request):
        return redirect("login")
    return None


def require_full_access(request):
    if not can_manage_records(request):
        return redirect("admin_home" if request.user.is_authenticated else "login")
    return None


def generate_patient_id():
    latest = Patient.objects.order_by('-id').first()
    next_id = (latest.id + 1) if latest else 1
    return f"HMS-P{next_id:05d}"


def generate_token_number():
    today = timezone.localdate()
    today_count = Appointment.objects.filter(date1=today).count() + 1
    return f"TKN-{today.strftime('%d%m')}-{today_count:03d}"

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
        role = request.POST.get('role', '')
        user = authenticate(username=u, password=p)
        if user is None:
            user_obj = User.objects.filter(email__iexact=u).first()
            if user_obj:
                user = authenticate(username=user_obj.username, password=p)
        if user is not None and role in ALL_ROLES:
            if role == "admin" and not user.is_staff:
                error = "role"
                return render(request,'login.html', locals())
            login(request, user)
            request.session['user_role'] = role
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
    redirect_response = require_dashboard_access(request)
    if redirect_response:
        return redirect_response

    today = timezone.localdate()
    dc = Doctor.objects.count()
    pc = Patient.objects.count()
    ac = Appointment.objects.count()
    dept = Doctor.objects.values_list('special', flat=True).distinct().count()
    appointments_today_count = Appointment.objects.filter(date1=today).count()
    today_appointments = appointments_today_count if appointments_today_count else ac
    total_beds = 120
    admitted_patients = Patient.objects.exclude(ward__isnull=True).exclude(ward__exact="").count()
    available_beds = max(total_beds - admitted_patients, 0)
    lab_reports = LabReport.objects.count()
    pharmacy_medicines = Medicine.objects.count()
    low_stock_count = Medicine.objects.filter(stock__lte=15).count()
    unread_notifications = Contact.objects.filter(isread="no").count()

    upcoming_qs = Appointment.objects.order_by('date1', 'time1')[:5]
    upcoming_appointments = []
    for appointment in upcoming_qs:
        upcoming_appointments.append({
            'patient': appointment.patient.name,
            'doctor': appointment.doctor.name,
            'department': appointment.doctor.special,
            'date': appointment.date1,
            'time': appointment.time1,
            'status': appointment.status or ('Confirmed' if appointment.date1 >= today else 'Pending'),
            'token': appointment.token_number or f'TKN-{appointment.id:03d}',
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
    appointment_trend_counts = []
    for delta in range(5, -1, -1):
        month_index = today.month - delta
        year = today.year + ((month_index - 1) // 12)
        month = ((month_index - 1) % 12) + 1
        label_date = date(year, month, 1)
        month_labels.append(label_date.strftime('%b'))
        month_counts.append(Patient.objects.filter(admission_date__year=year, admission_date__month=month).count())
        appointment_trend_counts.append(Appointment.objects.filter(date1__year=year, date1__month=month).count())

    departments = ["Cardiology", "Neurology", "Orthopedics", "Pediatrics", "General Medicine"]
    department_counts = [Doctor.objects.filter(department=department).count() for department in departments]
    bed_occupied_percent = int((admitted_patients / total_beds) * 100) if total_beds else 0

    patient_roster = Patient.objects.order_by('-id')[:8]
    doctor_roster = Doctor.objects.order_by('department', 'name')[:8]
    appointment_roster = Appointment.objects.order_by('-date1', '-time1')[:8]
    medicine_inventory = Medicine.objects.order_by('expiry_date', 'name')[:8]
    lab_report_rows = LabReport.objects.select_related('patient').order_by('-created_at')[:8]

    context = {
        'user_role': selected_role(request),
        'dc': dc,
        'pc': pc,
        'ac': ac,
        'dept': dept,
        'today_appointments': today_appointments,
        'available_beds': available_beds,
        'total_beds': total_beds,
        'admitted_patients': admitted_patients,
        'lab_reports': lab_reports,
        'pharmacy_medicines': pharmacy_medicines,
        'low_stock_count': low_stock_count,
        'unread_notifications': unread_notifications,
        'upcoming_appointments': upcoming_appointments,
        'recent_activities': activities,
        'patient_roster': patient_roster,
        'doctor_roster': doctor_roster,
        'appointment_roster': appointment_roster,
        'medicine_inventory': medicine_inventory,
        'lab_report_rows': lab_report_rows,
        'patient_overview_labels': json.dumps(month_labels),
        'patient_overview_counts': json.dumps(month_counts),
        'department_labels': json.dumps(departments),
        'department_counts': json.dumps(department_counts),
        'appointment_trend_counts': json.dumps(appointment_trend_counts),
        'bed_occupancy_counts': json.dumps([admitted_patients, available_beds]),
        'bed_occupied_percent': bed_occupied_percent
    }
    return render(request,'admin_home.html', context)


def module_context(request, title, subtitle, module_type):
    today = timezone.localdate()
    patient_count = Patient.objects.count()
    total_beds = 120
    admitted_patients = Patient.objects.exclude(ward__isnull=True).exclude(ward__exact="").count()
    available_beds = max(total_beds - admitted_patients, 0)
    month_labels = []
    month_counts = []
    for delta in range(5, -1, -1):
        month_index = today.month - delta
        year = today.year + ((month_index - 1) // 12)
        month = ((month_index - 1) % 12) + 1
        label_date = date(year, month, 1)
        month_labels.append(label_date.strftime('%b'))
        month_counts.append(Appointment.objects.filter(date1__year=year, date1__month=month).count())

    departments = ["Cardiology", "Neurology", "Orthopedics", "Pediatrics", "General Medicine"]
    return {
        'title': title,
        'subtitle': subtitle,
        'module_type': module_type,
        'unread_notifications': Contact.objects.filter(isread="no").count(),
        'patients': Patient.objects.order_by('-id')[:6],
        'appointments': Appointment.objects.order_by('-date1', '-time1')[:8],
        'available_beds': available_beds,
        'lab_reports': LabReport.objects.count(),
        'pharmacy_medicines': Medicine.objects.count(),
        'medicine_inventory': Medicine.objects.order_by('expiry_date', 'name'),
        'lab_report_rows': LabReport.objects.select_related('patient').order_by('-created_at'),
        'payment_rows': [
            {"invoice": "INV-1001", "patient": "Outpatient Visit", "amount": 2550, "status": "Paid"},
            {"invoice": "INV-1002", "patient": "Lab Billing", "amount": 1200, "status": "Pending"},
            {"invoice": "INV-1003", "patient": "Medicine Purchase", "amount": 850, "status": "Paid"},
        ],
        'patient_overview_labels': json.dumps(month_labels),
        'patient_overview_counts': json.dumps(month_counts),
        'department_labels': json.dumps(departments),
        'department_counts': json.dumps([Doctor.objects.filter(department=department).count() for department in departments]),
        'bed_occupancy_counts': json.dumps([admitted_patients, available_beds]),
    }


def add_report(request):
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    error = ""
    if request.method == "POST":
        patient_id = request.POST.get("patient")
        category = request.POST.get("category", "Blood Test")
        title = request.POST.get("title", "")
        remarks = request.POST.get("remarks", "")
        report_file = request.FILES.get("report_file")
        try:
            patient = Patient.objects.get(id=patient_id)
            LabReport.objects.create(
                patient=patient,
                category=category,
                title=title,
                remarks=remarks,
                report_file=report_file,
                status="Ready"
            )
            error = "no"
        except Exception:
            error = "yes"
    context = module_context(request, 'Add Report', 'Upload blood test and scan reports for patients.', 'add_report')
    context['error'] = error
    return render(request, 'module_page.html', context)


def view_reports(request):
    redirect_response = require_dashboard_access(request)
    if redirect_response:
        return redirect_response
    return render(request, 'module_page.html', module_context(request, 'View Reports', 'Track laboratory report status and downloads.', 'view_reports'))


def download_reports(request):
    redirect_response = require_dashboard_access(request)
    if redirect_response:
        return redirect_response
    return render(request, 'module_page.html', module_context(request, 'Download Report', 'Download uploaded laboratory report files.', 'view_reports'))


def download_report(request, pid):
    redirect_response = require_dashboard_access(request)
    if redirect_response:
        return redirect_response
    report = LabReport.objects.filter(id=pid).first()
    if not report or not report.report_file:
        raise Http404("Report file not found")
    try:
        return FileResponse(report.report_file.open('rb'), as_attachment=True, filename=os.path.basename(report.report_file.name))
    except FileNotFoundError:
        raise Http404("Report file not found")


def add_medicine(request):
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    error = ""
    if request.method == "POST":
        try:
            Medicine.objects.create(
                name=request.POST.get("name", ""),
                stock=request.POST.get("stock") or 0,
                expiry_date=request.POST.get("expiry_date"),
                prescribed_for=request.POST.get("prescribed_for", ""),
                dosage_notes=request.POST.get("dosage_notes", "")
            )
            error = "no"
        except Exception:
            error = "yes"
    context = module_context(request, 'Add Medicine', 'Register medicine stock, expiry, and prescribed records.', 'add_medicine')
    context['error'] = error
    return render(request, 'module_page.html', context)


def inventory(request):
    redirect_response = require_dashboard_access(request)
    if redirect_response:
        return redirect_response
    return render(request, 'module_page.html', module_context(request, 'Inventory', 'Monitor pharmacy medicines and low stock alerts.', 'inventory'))


def create_bill(request):
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    return render(request, 'module_page.html', module_context(request, 'Create Bill', 'Calculate consultation, lab, and medicine charges.', 'create_bill'))


def payment_history(request):
    redirect_response = require_dashboard_access(request)
    if redirect_response:
        return redirect_response
    return render(request, 'module_page.html', module_context(request, 'Payment History', 'Review printable invoice and payment records.', 'payment_history'))


def analytics(request):
    redirect_response = require_dashboard_access(request)
    if redirect_response:
        return redirect_response
    return render(request, 'module_page.html', module_context(request, 'Analytics', 'Hospital trends, department stats, and bed occupancy.', 'analytics'))

def Logout(request):
    request.session.pop('user_role', None)
    logout(request)
    return redirect('index')

def add_doctor(request):
    error=""
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    if request.method=='POST':
        n = request.POST['name']
        m = request.POST['mobile']
        sp = request.POST['special']
        dept = request.POST.get('department', sp)
        qualification = request.POST.get('qualification', '')
        availability = request.POST.get('availability', 'Available')
        assigned_patients = request.POST.get('assigned_patients') or 0
        try:
            Doctor.objects.create(
                name=n,
                mobile=m,
                special=sp,
                department=dept,
                qualification=qualification,
                availability=availability,
                assigned_patients=assigned_patients
            )
            error="no"
        except:
            error="yes"
    return render(request,'add_doctor.html', locals())

def view_doctor(request):
    redirect_response = require_dashboard_access(request)
    if redirect_response:
        return redirect_response
    doc = Doctor.objects.all()
    d = {'doc':doc, 'can_manage': can_manage_records(request)}
    return render(request,'view_doctor.html', d)

def Delete_Doctor(request,pid):
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    doctor = Doctor.objects.get(id=pid)
    doctor.delete()
    return redirect('view_doctor')

def edit_doctor(request,pid):
    error = ""
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    doctor = Doctor.objects.get(id=pid)
    if request.method == "POST":
        n1 = request.POST['name']
        m1 = request.POST['mobile']
        s1 = request.POST['special']
        d1 = request.POST.get('department', s1)
        q1 = request.POST.get('qualification', '')
        av1 = request.POST.get('availability', 'Available')
        ap1 = request.POST.get('assigned_patients') or 0

        doctor.name = n1
        doctor.mobile = m1
        doctor.special = s1
        doctor.department = d1
        doctor.qualification = q1
        doctor.availability = av1
        doctor.assigned_patients = ap1

        try:
            doctor.save()
            error = "no"
        except:
            error = "yes"
    return render(request, 'edit_doctor.html', locals())

def add_patient(request):
    error = ""
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    if request.method == 'POST':
        n = request.POST['name']
        g = request.POST['gender']
        m = request.POST['mobile']
        a = request.POST['address']
        w = request.POST.get('ward', '')
        age = request.POST.get('age') or None
        blood_group = request.POST.get('blood_group', '')
        disease = request.POST.get('disease', '')
        admission_date = request.POST.get('admission_date') or None
        try:
            Patient.objects.create(
                name=n,
                patient_id=generate_patient_id(),
                age=age,
                gender=g,
                mobile=m,
                blood_group=blood_group,
                disease=disease,
                admission_date=admission_date,
                address=a,
                ward=w
            )
            error = "no"
        except:
            error = "yes"
    return render(request,'add_patient.html', locals())

def view_patient(request):
    redirect_response = require_dashboard_access(request)
    if redirect_response:
        return redirect_response
    pat = Patient.objects.all()
    d = {'pat':pat, 'can_manage': can_manage_records(request)}
    return render(request,'view_patient.html', d)

def Delete_Patient(request,pid):
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    patient = Patient.objects.get(id=pid)
    patient.delete()
    return redirect('view_patient')

def edit_patient(request,pid):
    error = ""
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    user = request.user
    patient = Patient.objects.get(id=pid)
    if request.method == "POST":
        n1 = request.POST['name']
        m1 = request.POST['mobile']
        g1 = request.POST['gender']
        a1 = request.POST['address']
        w1 = request.POST.get('ward', '')
        age1 = request.POST.get('age') or None
        bg1 = request.POST.get('blood_group', '')
        disease1 = request.POST.get('disease', '')
        ad1 = request.POST.get('admission_date') or None

        patient.name = n1
        if not patient.patient_id:
            patient.patient_id = generate_patient_id()
        patient.age = age1
        patient.mobile = m1
        patient.gender = g1
        patient.blood_group = bg1
        patient.disease = disease1
        patient.admission_date = ad1
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
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    doctor1 = Doctor.objects.all()
    patient1 = Patient.objects.all()
    if request.method=='POST':
        d = request.POST['doctor']
        p = request.POST['patient']
        d1 = request.POST['date']
        t = request.POST['time']
        status = request.POST.get('status', 'Pending')
        doctor = Doctor.objects.filter(name=d).first()
        patient = Patient.objects.filter(name=p).first()
        try:
            Appointment.objects.create(
                doctor=doctor,
                patient=patient,
                date1=d1,
                time1=t,
                status=status,
                token_number=generate_token_number()
            )
            error="no"
        except:
            error="yes"
    d = {'doctor':doctor1,'patient':patient1,'error':error}
    return render(request,'add_appointment.html', d)

def view_appointment(request):
    redirect_response = require_dashboard_access(request)
    if redirect_response:
        return redirect_response
    appointment = Appointment.objects.all()
    d = {'appointment':appointment, 'can_manage': can_manage_records(request)}
    return render(request,'view_appointment.html', d)

def Delete_Appointment(request,pid):
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    appointment1 = Appointment.objects.get(id=pid)
    appointment1.delete()
    return redirect('view_appointment')

def unread_queries(request):
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    contact = Contact.objects.filter(isread="no")
    return render(request,'unread_queries.html', locals())

def read_queries(request):
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    contact = Contact.objects.filter(isread="yes")
    return render(request,'read_queries.html', locals())

def view_queries(request,pid):
    redirect_response = require_full_access(request)
    if redirect_response:
        return redirect_response
    contact = Contact.objects.get(id=pid)
    contact.isread = "yes"
    contact.save()
    return render(request,'view_queries.html', locals())


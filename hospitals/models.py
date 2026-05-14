from django.db import models

# Create your models here.

class Doctor(models.Model):
    DEPARTMENT_CHOICES = (
        ("Cardiology", "Cardiology"),
        ("Neurology", "Neurology"),
        ("Orthopedics", "Orthopedics"),
        ("Pediatrics", "Pediatrics"),
        ("General Medicine", "General Medicine"),
    )
    AVAILABILITY_CHOICES = (
        ("Available", "Available"),
        ("On Duty", "On Duty"),
        ("Unavailable", "Unavailable"),
    )

    name = models.CharField(max_length=50)
    mobile = models.IntegerField()
    special = models.CharField(max_length=50)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, default="General Medicine")
    qualification = models.CharField(max_length=80, blank=True, default="")
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default="Available")
    assigned_patients = models.PositiveIntegerField(default=0)

    def __str__(self):
       return self.name;

class Patient(models.Model):
    BLOOD_GROUP_CHOICES = (
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("O+", "O+"),
        ("O-", "O-"),
    )
    WARD_CHOICES = (
        ("General Ward", "General Ward"),
        ("ICU", "ICU"),
        ("Emergency", "Emergency"),
        ("Pediatrics", "Pediatrics"),
        ("Maternity", "Maternity"),
        ("Private Room", "Private Room"),
    )

    name = models.CharField(max_length=50)
    patient_id = models.CharField(max_length=20, blank=True, default="")
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10)
    mobile = models.IntegerField(null=True)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True, default="")
    disease = models.CharField(max_length=100, blank=True, default="")
    admission_date = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=50)
    ward = models.CharField(max_length=50, choices=WARD_CHOICES, null=True, blank=True)

    def __str__(self):
       return self.name;

class Appointment(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Cancelled", "Cancelled"),
        ("Completed", "Completed"),
    )

    doctor = models.ForeignKey(Doctor,on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    date1 = models.DateField()
    time1 = models.TimeField()
    token_number = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    def __str__(self):
       return f"{self.doctor.name}--{self.patient.name}";

class Contact(models.Model):
    name = models.CharField(max_length=100, null=True)
    contact = models.CharField(max_length=15, null=True)
    email = models.CharField(max_length=50, null=True)
    subject = models.CharField(max_length=100, null=True)
    message = models.CharField(max_length=300, null=True)
    msgdate = models.DateField(null=True)
    isread = models.CharField(max_length=10,null=True)

    def __str__(self):
        return self.id


class LabReport(models.Model):
    REPORT_CHOICES = (
        ("Blood Test", "Blood Test"),
        ("Scan", "Scan"),
        ("X-Ray", "X-Ray"),
        ("Urine Test", "Urine Test"),
        ("Other", "Other"),
    )
    STATUS_CHOICES = (
        ("Ready", "Ready"),
        ("Processing", "Processing"),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    category = models.CharField(max_length=50, choices=REPORT_CHOICES)
    title = models.CharField(max_length=100)
    report_file = models.FileField(upload_to="reports/")
    remarks = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Ready")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.patient.name}"


class Medicine(models.Model):
    name = models.CharField(max_length=100)
    stock = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField()
    prescribed_for = models.CharField(max_length=100, blank=True, default="")
    dosage_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def status(self):
        return "Low Stock" if self.stock <= 15 else "Available"

    def __str__(self):
        return self.name

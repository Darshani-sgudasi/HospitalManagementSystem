"""HospitalManagementSystem URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from hospitals.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('about/', About, name="about"),
    path('',Index,name='index'),
    path('contact', contact, name='contact'),
    path('login', adminlogin, name='login'),
    path('forgot-password', forgot_password, name='forgot_password'),
    path('reset-password/<int:uid>/<str:token>', reset_password, name='reset_password'),
    path('admin_home', admin_home, name='admin_home'),
    path('logout/', Logout, name='logout'),
    path('add_doctor', add_doctor, name='add_doctor'),
    path('view_doctor', view_doctor, name='view_doctor'),
    path('delete_doctor/<int:pid>', Delete_Doctor, name='delete_doctor'),
    path('signup', signup, name='signup'),
    path('add_patient', add_patient, name='add_patient'),
    path('view_patient', view_patient, name='view_patient'),
    path('delete_patient/<int:pid>', Delete_Patient, name='delete_patient'),
    path('add_appointment', add_appointment, name='add_appointment'),
    path('view_appointment', view_appointment, name='view_appointment'),
    path('delete_appointment/<int:pid>', Delete_Appointment, name='delete_appointment'),
    path('edit_doctor/<int:pid>',edit_doctor,name='edit_doctor'),
    path('edit_patient/<int:pid>',edit_patient,name='edit_patient'),
    path('unread_queries', unread_queries, name='unread_queries'),
    path('read_queries', read_queries, name='read_queries'),
    path('view_queries/<int:pid>', view_queries, name='view_queries'),
    path('add_report', add_report, name='add_report'),
    path('view_reports', view_reports, name='view_reports'),
    path('download_reports', download_reports, name='download_reports'),
    path('download_report/<int:pid>', download_report, name='download_report'),
    path('add_medicine', add_medicine, name='add_medicine'),
    path('inventory', inventory, name='inventory'),
    path('create_bill', create_bill, name='create_bill'),
    path('payment_history', payment_history, name='payment_history'),
    path('analytics', analytics, name='analytics'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

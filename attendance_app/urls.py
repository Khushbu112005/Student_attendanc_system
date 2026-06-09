from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Student CRUD
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('students/add/', views.StudentCreateView.as_view(), name='student_add'),
    path('students/<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_edit'),
    path('students/<int:pk>/delete/', views.StudentDeleteView.as_view(), name='student_delete'),

    # Teacher Listing & CRUD
    path('teachers/', views.TeacherListView.as_view(), name='teacher_list'),
    path('teachers/add/', views.TeacherCreateView.as_view(), name='teacher_add'),
    path('teachers/<int:pk>/edit/', views.TeacherUpdateView.as_view(), name='teacher_edit'),
    path('teachers/<int:pk>/delete/', views.TeacherDeleteView.as_view(), name='teacher_delete'),

    # Attendance Pages (Templates serve as SPA containers)
    path('attendance/mark/', views.MarkAttendanceView.as_view(), name='mark_attendance'),
    path('attendance/report/', views.AttendanceReportView.as_view(), name='attendance_report'),
    path('attendance/<int:session_id>/edit/', views.AttendanceEditView.as_view(), name='attendance_edit'),
    path('attendance/<int:session_id>/export/', views.ExportCSVView.as_view(), name='export_csv'),

    # DYNAMIC JSON API Endpoints
    path('api/students/', views.APIStudentsView.as_view(), name='api_students'),
    path('api/sessions/', views.APISessionsView.as_view(), name='api_sessions'),
    path('api/mark/', views.APIMarkView.as_view(), name='api_mark'),
    path('api/report/', views.APIReportView.as_view(), name='api_report'),
    path('api/edit/', views.APIEditView.as_view(), name='api_edit'),
]

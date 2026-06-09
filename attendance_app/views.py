import datetime
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse

from .models import Student, Teacher, AttendanceSession, AttendanceEntry, ActivityLog, AttendanceAuditLog
from .forms import StudentForm, TeacherForm
from .services import AttendanceService

# Custom Error Views
def custom_404_view(request, exception=None):
    return render(request, '404.html', status=404)

def custom_500_view(request):
    return render(request, '500.html', status=500)


from django.contrib.auth.mixins import UserPassesTestMixin

class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('dashboard')
        return super().handle_no_permission()


class DashboardView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        if hasattr(self.request.user, 'student_profile'):
            return ['students/dashboard.html']
        return ['dashboard.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if hasattr(user, 'student_profile'):
            # Student view context
            student = user.student_profile
            entries = AttendanceEntry.objects.filter(student=student).select_related('attendance_session', 'attendance_session__marked_by').order_by('-attendance_session__attendance_date')
            
            total = entries.count()
            present = entries.filter(status='Present').count()
            absent = entries.filter(status='Absent').count()
            percentage = (present / total * 100) if total > 0 else 0
            
            context['student'] = student
            context['entries'] = entries
            context['total_days'] = total
            context['present_days'] = present
            context['absent_days'] = absent
            context['attendance_percentage'] = round(percentage, 1)
        else:
            # General / Teacher view context
            today = datetime.date.today()
            context['total_students'] = Student.objects.count()
            context['total_teachers'] = Teacher.objects.count()
            
            today_sessions = AttendanceSession.objects.filter(attendance_date=today)
            context['present_today'] = AttendanceEntry.objects.filter(
                attendance_session__in=today_sessions, status='Present'
            ).count()
            context['absent_today'] = AttendanceEntry.objects.filter(
                attendance_session__in=today_sessions, status='Absent'
            ).count()
            
            context['recent_activities'] = ActivityLog.objects.select_related('user').all()[:10]
            
        return context


# --- STUDENT CRUD ---

class StudentListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Student
    template_name = 'students/student_list.html'
    context_object_name = 'students'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '').strip()
        class_filter = self.request.GET.get('class_name', '').strip()
        section_filter = self.request.GET.get('section', '').strip()

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(roll_number__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        if class_filter:
            queryset = queryset.filter(class_name__iexact=class_filter)
        if section_filter:
            queryset = queryset.filter(section__iexact=section_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['classes'] = Student.objects.values_list('class_name', flat=True).distinct().order_by('class_name')
        context['sections'] = Student.objects.values_list('section', flat=True).distinct().order_by('section')
        context['search_val'] = self.request.GET.get('search', '')
        context['class_val'] = self.request.GET.get('class_name', '')
        context['section_val'] = self.request.GET.get('section', '')
        return context


class StudentCreateView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('student_list')
    success_message = "Student added successfully."

    def form_valid(self, form):
        student = form.save(commit=False)
        username = student.email.split('@')[0] if student.email else student.name.lower().replace(' ', '.')
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            
        user = User.objects.create_user(
            username=username,
            email=student.email or '',
            password="password123"
        )
        student.user = user
        student.save()
        form.save_m2m()
        
        ActivityLog.objects.create(
            activity_type='Student Added',
            description=f"Added student: {student.name} (Roll: {student.roll_number}, Class: {student.class_name}-{student.section})",
            user=self.request.user
        )
        messages.success(self.request, self.success_message)
        return redirect(self.success_url)


class StudentUpdateView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'students/student_form.html'
    success_url = reverse_lazy('student_list')
    success_message = "Student updated successfully."

    def form_valid(self, form):
        student = form.save()
        if not student.user:
            username = student.email.split('@')[0] if student.email else student.name.lower().replace(' ', '.')
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            user = User.objects.create_user(username=username, email=student.email or '', password="password123")
            student.user = user
            student.save()
        elif student.email:
            u = student.user
            u.email = student.email
            u.save()

        ActivityLog.objects.create(
            activity_type='Student Edited',
            description=f"Updated student: {student.name} (Roll: {student.roll_number}, Class: {student.class_name}-{student.section})",
            user=self.request.user
        )
        messages.success(self.request, self.success_message)
        return redirect(self.success_url)


class StudentDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Student
    template_name = 'students/student_confirm_delete.html'
    success_url = reverse_lazy('student_list')

    def form_valid(self, form):
        student = self.get_object()
        user = student.user
        student_desc = f"{student.name} (Roll: {student.roll_number}, Class: {student.class_name}-{student.section})"
        response = super().form_valid(form)
        if user:
            user.delete()
        ActivityLog.objects.create(
            activity_type='Student Deleted',
            description=f"Deleted student: {student_desc}",
            user=self.request.user
        )
        messages.success(self.request, "Student record deleted successfully.")
        return response


# --- TEACHER CRUD ---

class TeacherListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Teacher
    template_name = 'teachers/teacher_list.html'
    context_object_name = 'teachers'
    paginate_by = 25


class TeacherCreateView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'teachers/teacher_form.html'
    success_url = reverse_lazy('teacher_list')
    success_message = "Teacher added successfully."

    def form_valid(self, form):
        response = super().form_valid(form)
        ActivityLog.objects.create(
            activity_type='Teacher Added',
            description=f"Added teacher: {self.object.name} (ID: {self.object.employee_id}, Subject: {self.object.subject})",
            user=self.request.user
        )
        return response


class TeacherUpdateView(LoginRequiredMixin, StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'teachers/teacher_form.html'
    success_url = reverse_lazy('teacher_list')
    success_message = "Teacher updated successfully."

    def form_valid(self, form):
        response = super().form_valid(form)
        ActivityLog.objects.create(
            activity_type='Teacher Edited',
            description=f"Updated teacher: {self.object.name} (ID: {self.object.employee_id})",
            user=self.request.user
        )
        return response


class TeacherDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Teacher
    template_name = 'students/student_confirm_delete.html'
    success_url = reverse_lazy('teacher_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_teacher'] = True
        return context

    def form_valid(self, form):
        teacher = self.get_object()
        teacher_desc = f"{teacher.name} (ID: {teacher.employee_id})"
        response = super().form_valid(form)
        ActivityLog.objects.create(
            activity_type='Teacher Deleted',
            description=f"Deleted teacher: {teacher_desc}",
            user=self.request.user
        )
        messages.success(self.request, "Teacher record deleted successfully.")
        return response


# --- ATTENDANCE VIEWS ---

class MarkAttendanceView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request):
        classes = Student.objects.values_list('class_name', flat=True).distinct().order_by('class_name')
        sections = Student.objects.values_list('section', flat=True).distinct().order_by('section')
        
        date_str = request.GET.get('date', '').strip()
        class_name = request.GET.get('class_name', '').strip()
        section = request.GET.get('section', '').strip()
        
        context = {
            'classes': classes,
            'sections': sections,
            'date_val': date_str,
            'class_val': class_name,
            'section_val': section,
            'today_str': datetime.date.today().strftime("%Y-%m-%d")
        }
        return render(request, 'attendance/mark_attendance.html', context)


class AttendanceReportView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request):
        context = {
            'today_str': datetime.date.today().strftime("%Y-%m-%d"),
            'date_val': request.GET.get('date', '').strip(),
            'session_val': request.GET.get('session_id', '').strip()
        }
        return render(request, 'attendance/attendance_report.html', context)


class AttendanceEditView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id)
        entries = session.entries.select_related('student').all().order_by('student__roll_number')
        context = {
            'session': session,
            'entries': entries,
        }
        return render(request, 'attendance/attendance_edit.html', context)


class ExportCSVView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request, session_id):
        session = get_object_or_404(AttendanceSession, id=session_id)
        return AttendanceService.export_csv(session)


# --- DYNAMIC JSON APIs (NO STATIC PAGES IN WORKFLOW) ---

class APISessionsView(LoginRequiredMixin, StaffRequiredMixin, View):
    """Returns JSON list of attendance sessions for a specific date."""
    def get(self, request):
        date_str = request.GET.get('date', '').strip()
        if not date_str:
            return JsonResponse({'status': 'error', 'message': 'Date is required.'}, status=400)
        try:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid date format.'}, status=400)

        sessions = AttendanceSession.objects.filter(attendance_date=date).order_by('class_name', 'section')
        data = []
        for s in sessions:
            data.append({
                'id': s.id,
                'class_name': s.class_name,
                'section': s.section,
                'marked_by': s.marked_by.username if s.marked_by else 'System'
            })
        return JsonResponse({'status': 'success', 'sessions': data})


class APIStudentsView(LoginRequiredMixin, StaffRequiredMixin, View):
    """Returns students in a class or checks if attendance already exists."""
    def get(self, request):
        date_str = request.GET.get('date', '').strip()
        class_name = request.GET.get('class_name', '').strip()
        section = request.GET.get('section', '').strip()

        if not (date_str and class_name and section):
            return JsonResponse({'status': 'error', 'message': 'Missing required fields.'}, status=400)

        try:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid date format.'}, status=400)

        if date > datetime.date.today():
            return JsonResponse({'status': 'error', 'message': 'Future attendance records cannot be created or modified.'}, status=400)

        # 1. Check if session already exists
        existing_session = AttendanceSession.objects.filter(
            attendance_date=date, class_name=class_name, section=section
        ).first()

        if existing_session:
            return JsonResponse({
                'status': 'success',
                'exists': True,
                'session_id': existing_session.id,
                'message': 'Attendance sheet already exists for this date.'
            })

        # 2. Get students
        students = Student.objects.filter(class_name=class_name, section=section).order_by('roll_number')
        student_list = [{'id': s.id, 'name': s.name, 'roll_number': s.roll_number} for s in students]

        return JsonResponse({
            'status': 'success',
            'exists': False,
            'students': student_list
        })


class APIMarkView(LoginRequiredMixin, StaffRequiredMixin, View):
    """Saves attendance dynamically via JSON POST."""
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)

        date_str = data.get('date', '').strip()
        class_name = data.get('class_name', '').strip()
        section = data.get('section', '').strip()
        entries_input = data.get('entries', {})

        if not (date_str and class_name and section):
            return JsonResponse({'status': 'error', 'message': 'Missing session parameters.'}, status=400)

        try:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid date format.'}, status=400)

        # Format student IDs to integers
        entries_data = {}
        for s_id, status in entries_input.items():
            try:
                entries_data[int(s_id)] = status
            except ValueError:
                continue

        try:
            session = AttendanceService.mark_attendance(
                date=date,
                class_name=class_name,
                section=section,
                marked_by=request.user,
                entries_data=entries_data
            )
            return JsonResponse({
                'status': 'success',
                'session_id': session.id,
                'message': f"Attendance saved successfully for Class {class_name}-{section} on {date}."
            })
        except ValidationError as e:
            return JsonResponse({'status': 'error', 'message': e.message if hasattr(e, 'message') else str(e)}, status=400)


class APIReportView(LoginRequiredMixin, StaffRequiredMixin, View):
    """Returns JSON report summary and entry list."""
    def get(self, request):
        session_id = request.GET.get('session_id', '').strip()
        if not session_id:
            return JsonResponse({'status': 'error', 'message': 'Session ID is required.'}, status=400)

        session = get_object_or_404(AttendanceSession, id=session_id)
        entries = session.entries.select_related('student').all().order_by('student__roll_number')

        total = entries.count()
        present = entries.filter(status='Present').count()
        absent = entries.filter(status='Absent').count()

        student_entries = []
        for e in entries:
            student_entries.append({
                'student_id': e.student.id,
                'name': e.student.name,
                'roll_number': e.student.roll_number,
                'class_name': e.student.class_name,
                'section': e.student.section,
                'status': e.status
            })

        return JsonResponse({
            'status': 'success',
            'session': {
                'id': session.id,
                'class_name': session.class_name,
                'section': session.section,
                'date': session.attendance_date.strftime("%Y-%m-%d"),
                'marked_by': session.marked_by.username if session.marked_by else 'System'
            },
            'summary': {
                'total': total,
                'present': present,
                'absent': absent
            },
            'entries': student_entries
        })


class APIEditView(LoginRequiredMixin, StaffRequiredMixin, View):
    """Updates attendance sheet dynamically via JSON POST."""
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)

        session_id = data.get('session_id')
        entries_input = data.get('entries', {})
        edit_reason = data.get('edit_reason', '').strip()

        if not session_id:
            return JsonResponse({'status': 'error', 'message': 'Session ID is required.'}, status=400)
        if not edit_reason:
            return JsonResponse({'status': 'error', 'message': 'Reason for modification is mandatory.'}, status=400)

        session = get_object_or_404(AttendanceSession, id=session_id)

        # Format student IDs
        entries_data = {}
        for s_id, status in entries_input.items():
            try:
                entries_data[int(s_id)] = status
            except ValueError:
                continue

        try:
            AttendanceService.update_attendance(
                session=session,
                edited_by=request.user,
                entries_data=entries_data,
                edit_reason=edit_reason
            )
            return JsonResponse({
                'status': 'success',
                'message': 'Attendance record corrected successfully.'
            })
        except ValidationError as e:
            return JsonResponse({'status': 'error', 'message': e.message if hasattr(e, 'message') else str(e)}, status=400)

from django.db import models
from django.contrib.auth.models import User

class Student(models.Model):
    name = models.CharField(max_length=150)
    roll_number = models.IntegerField()
    class_name = models.CharField(max_length=50)
    section = models.CharField(max_length=10)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('roll_number', 'class_name', 'section')
        indexes = [
            models.Index(fields=['class_name', 'section']),
        ]
        ordering = ['class_name', 'section', 'roll_number']

    def __str__(self) -> str:
        return f"{self.name} (Roll: {self.roll_number}, Class: {self.class_name}-{self.section})"


class Teacher(models.Model):
    name = models.CharField(max_length=150)
    employee_id = models.CharField(max_length=50, unique=True)
    subject = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return f"{self.name} ({self.employee_id}) - {self.subject}"


class AttendanceSession(models.Model):
    attendance_date = models.DateField()
    class_name = models.CharField(max_length=50)
    section = models.CharField(max_length=10)
    marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='marked_sessions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('attendance_date', 'class_name', 'section')
        indexes = [
            models.Index(fields=['attendance_date']),
        ]
        ordering = ['-attendance_date', 'class_name', 'section']

    def __str__(self) -> str:
        return f"Session: {self.class_name}-{self.section} on {self.attendance_date}"


class AttendanceEntry(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
    ]
    attendance_session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='entries')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_entries')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ('attendance_session', 'student')
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return f"{self.student.name} - {self.status} on {self.attendance_session.attendance_date}"


class AttendanceAuditLog(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
    ]
    attendance_entry = models.ForeignKey(AttendanceEntry, on_delete=models.CASCADE, related_name='audit_logs')
    old_status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    new_status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='attendance_edits')
    edited_at = models.DateTimeField(auto_now_add=True)
    edit_reason = models.TextField()

    class Meta:
        ordering = ['-edited_at']

    def __str__(self) -> str:
        return f"Edit: {self.attendance_entry.student.name} from {self.old_status} to {self.new_status}"


class ActivityLog(models.Model):
    activity_type = models.CharField(max_length=50)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='activities')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.activity_type} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

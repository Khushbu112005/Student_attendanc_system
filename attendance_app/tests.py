import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Student, Teacher, AttendanceSession, AttendanceEntry, AttendanceAuditLog, ActivityLog
from .services import AttendanceService

class AttendanceSystemTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username="testteacher", password="testpassword")
        
        # Create some test students
        self.student1 = Student.objects.create(
            name="Aarav Mehta", roll_number=1, class_name="B.Tech CSE", section="A", email="aarav@test.com"
        )
        self.student2 = Student.objects.create(
            name="Ananya Iyer", roll_number=2, class_name="B.Tech CSE", section="A", email="ananya@test.com"
        )
        
        # Create a test teacher
        self.teacher = Teacher.objects.create(
            name="Mr. Rajesh Kumar", employee_id="TCH101", subject="Software Engineering", email="rajesh@test.com"
        )
        
        self.client = Client()

    def test_student_uniqueness_validation(self):
        """Tests database-level unique constraint on (roll_number, class_name, section)."""
        # Creating student with same class, section, and roll number should raise IntegrityError
        with self.assertRaises(Exception):
            Student.objects.create(
                name="Arjun Goel", roll_number=1, class_name="B.Tech CSE", section="A"
            )

    def test_teacher_creation(self):
        """Tests that a teacher can be created successfully."""
        self.assertEqual(Teacher.objects.count(), 1)
        teacher = Teacher.objects.get(employee_id="TCH101")
        self.assertEqual(teacher.name, "Mr. Rajesh Kumar")
        self.assertEqual(teacher.subject, "Software Engineering")

    def test_attendance_marking_workflow(self):
        """Tests AttendanceService.mark_attendance completes successfully with defaults."""
        today = datetime.date.today()
        entries_data = {
            self.student1.id: 'Present',
            self.student2.id: 'Absent',
        }

        # Mark attendance
        session = AttendanceService.mark_attendance(
            date=today,
            class_name="B.Tech CSE",
            section="A",
            marked_by=self.user,
            entries_data=entries_data
        )

        self.assertEqual(AttendanceSession.objects.count(), 1)
        self.assertEqual(AttendanceEntry.objects.count(), 2)

        entry1 = AttendanceEntry.objects.get(attendance_session=session, student=self.student1)
        entry2 = AttendanceEntry.objects.get(attendance_session=session, student=self.student2)

        self.assertEqual(entry1.status, 'Present')
        self.assertEqual(entry2.status, 'Absent')

        # Check ActivityLog
        self.assertTrue(
            ActivityLog.objects.filter(activity_type='Attendance Marked').exists()
        )

    def test_duplicate_attendance_prevention(self):
        """Tests that marking attendance for the same date/class/section twice raises ValidationError."""
        today = datetime.date.today()
        entries_data = {
            self.student1.id: 'Present',
            self.student2.id: 'Present',
        }

        # First marking
        AttendanceService.mark_attendance(
            date=today,
            class_name="B.Tech CSE",
            section="A",
            marked_by=self.user,
            entries_data=entries_data
        )

        # Second marking should fail with ValidationError
        with self.assertRaises(ValidationError) as ctx:
            AttendanceService.mark_attendance(
                date=today,
                class_name="B.Tech CSE",
                section="A",
                marked_by=self.user,
                entries_data=entries_data
            )
        self.assertIn("Attendance already exists", str(ctx.exception))

    def test_prevent_editing_future_attendance(self):
        """Tests that marking or updating attendance for future dates is prevented."""
        future_date = datetime.date.today() + datetime.timedelta(days=1)
        entries_data = {
            self.student1.id: 'Present',
            self.student2.id: 'Present',
        }

        # Marking future attendance should raise ValidationError
        with self.assertRaises(ValidationError) as ctx:
            AttendanceService.mark_attendance(
                date=future_date,
                class_name="B.Tech CSE",
                section="A",
                marked_by=self.user,
                entries_data=entries_data
            )
        self.assertIn("Future attendance records cannot be created", str(ctx.exception))

    def test_attendance_correction_and_audit_log(self):
        """Tests updating attendance and verifying correct audit logging."""
        today = datetime.date.today()
        entries_data = {
            self.student1.id: 'Present',
            self.student2.id: 'Present',
        }

        # Mark initially
        session = AttendanceService.mark_attendance(
            date=today,
            class_name="B.Tech CSE",
            section="A",
            marked_by=self.user,
            entries_data=entries_data
        )

        # Correct Bob Jones (student2) to Absent
        edit_data = {
            self.student1.id: 'Present',
            self.student2.id: 'Absent',
        }
        
        AttendanceService.update_attendance(
            session=session,
            edited_by=self.user,
            entries_data=edit_data,
            edit_reason="Student left school early."
        )

        # Check updated status
        entry2 = AttendanceEntry.objects.get(attendance_session=session, student=self.student2)
        self.assertEqual(entry2.status, 'Absent')

        # Check Audit Log
        self.assertEqual(AttendanceAuditLog.objects.count(), 1)
        audit = AttendanceAuditLog.objects.first()
        self.assertEqual(audit.attendance_entry, entry2)
        self.assertEqual(audit.old_status, 'Present')
        self.assertEqual(audit.new_status, 'Absent')
        self.assertEqual(audit.edited_by, self.user)
        self.assertEqual(audit.edit_reason, "Student left school early.")

    def test_views_require_authentication(self):
        """Tests login restriction on core dashboard and list views."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirects to login page
        
        response = self.client.get(reverse('student_list'))
        self.assertEqual(response.status_code, 302)

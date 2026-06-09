import csv
import datetime
from typing import Dict, List, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.contrib.auth.models import User
from .models import Student, AttendanceSession, AttendanceEntry, AttendanceAuditLog, ActivityLog

class AttendanceService:
    @staticmethod
    def mark_attendance(
        date: datetime.date,
        class_name: str,
        section: str,
        marked_by: User,
        entries_data: Dict[int, str]  # dict of student_id -> status ('Present' or 'Absent')
    ) -> AttendanceSession:
        """
        Marks attendance for a class on a specific date.
        Validates future date, pre-existing session, and empty student list.
        Uses atomic transactions and bulk creation.
        """
        # 1. Prevent Future Dates
        if date > datetime.date.today():
            raise ValidationError("Future attendance records cannot be created or modified.")

        with transaction.atomic():
            # 2. Check for pre-existing session
            if AttendanceSession.objects.filter(
                attendance_date=date, class_name=class_name, section=section
            ).exists():
                raise ValidationError("Attendance already exists for this date. Please edit the existing attendance record.")

            # 3. Check for empty class
            students = Student.objects.filter(class_name=class_name, section=section)
            if not students.exists():
                raise ValidationError("No students found for selected class and section.")

            # 4. Create the session
            session = AttendanceSession.objects.create(
                attendance_date=date,
                class_name=class_name,
                section=section,
                marked_by=marked_by
            )

            # 5. Build and bulk create entries
            entries = []
            for student in students:
                # Default status is 'Present' if not provided in entries_data
                status = entries_data.get(student.id, 'Present')
                if status not in ('Present', 'Absent'):
                    status = 'Present'
                
                entries.append(
                    AttendanceEntry(
                        attendance_session=session,
                        student=student,
                        status=status
                    )
                )

            AttendanceEntry.objects.bulk_create(entries)

            # 6. Log the activity
            ActivityLog.objects.create(
                activity_type='Attendance Marked',
                description=f"Attendance marked for class {class_name}-{section} on {date}.",
                user=marked_by
            )

            return session

    @staticmethod
    def update_attendance(
        session: AttendanceSession,
        edited_by: User,
        entries_data: Dict[int, str],  # dict of student_id -> status ('Present' or 'Absent')
        edit_reason: str
    ) -> None:
        """
        Updates attendance entries for an existing session.
        Validates future date, mandatory reason.
        Saves changes and logs edits in AttendanceAuditLog.
        """
        # 1. Prevent Future Dates
        if session.attendance_date > datetime.date.today():
            raise ValidationError("Future attendance records cannot be created or modified.")

        # 2. Require modification reason
        edit_reason = edit_reason.strip() if edit_reason else ""
        if not edit_reason:
            raise ValidationError("Reason for modification is mandatory.")

        with transaction.atomic():
            # Fetch existing entries
            existing_entries = {
                entry.student_id: entry for entry in session.entries.all()
            }

            audit_logs = []
            entries_to_update = []

            for student_id, new_status in entries_data.items():
                if student_id in existing_entries:
                    entry = existing_entries[student_id]
                    old_status = entry.status
                    
                    if old_status != new_status:
                        # Update the entry status
                        entry.status = new_status
                        entries_to_update.append(entry)

                        # Generate audit log entry
                        audit_logs.append(
                            AttendanceAuditLog(
                                attendance_entry=entry,
                                old_status=old_status,
                                new_status=new_status,
                                edited_by=edited_by,
                                edit_reason=edit_reason
                            )
                        )

            # Bulk updates for modified entries
            if entries_to_update:
                AttendanceEntry.objects.bulk_update(entries_to_update, ['status'])
                
            # Bulk create audit logs
            if audit_logs:
                AttendanceAuditLog.objects.bulk_create(audit_logs)

            # Log overall edit activity
            ActivityLog.objects.create(
                activity_type='Attendance Edited',
                description=f"Attendance corrected for class {session.class_name}-{session.section} on {session.attendance_date}.",
                user=edited_by
            )

    @staticmethod
    def export_csv(session: AttendanceSession) -> HttpResponse:
        """
        Generates CSV for the class-wise attendance session.
        """
        response = HttpResponse(content_type='text/csv')
        filename = f"attendance_{session.class_name}_{session.section}_{session.attendance_date}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Student Name', 'Roll Number', 'Class', 'Section', 'Status'])

        entries = session.entries.select_related('student').all().order_by('student__roll_number')
        for entry in entries:
            writer.writerow([
                entry.student.name,
                entry.student.roll_number,
                entry.student.class_name,
                entry.student.section,
                entry.status
            ])

        return response

import datetime
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from attendance_app.models import Student, Teacher, AttendanceSession, AttendanceEntry, ActivityLog
from attendance_app.services import AttendanceService

class Command(BaseCommand):
    help = "Seeds the database with teachers, students, a default admin user, and sample attendance history."

    def handle(self, *args, **options):
        self.stdout.write("Seeding database...")
        
        with transaction.atomic():
            # 1. Create default admin user
            admin_user, created = User.objects.get_or_create(username="admin")
            if created:
                admin_user.set_password("adminpassword")
                admin_user.email = "admin@attendance.com"
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.save()
                self.stdout.write(self.style.SUCCESS("Created default user: admin / adminpassword"))
            else:
                self.stdout.write("Admin user already exists.")

            # Clear existing application records to make seeding clean and repeatable
            AttendanceSession.objects.all().delete()
            # Delete all student User records (non-staff, non-superuser)
            User.objects.filter(is_staff=False, is_superuser=False).delete()
            Student.objects.all().delete()
            Teacher.objects.all().delete()
            ActivityLog.objects.all().delete()
            self.stdout.write("Cleaned existing student, teacher, session, activity records, and student user accounts.")

            # 2. Seed Teachers
            teachers_data = [
                ("Rahul Sharma", "TCH001", "Software Engineering", "9876543210", "rahul.sharma@school.com", "rahul"),
                ("Priyanka Sen", "TCH002", "Data Structures & Algorithms", "9876543211", "priyanki.sen@school.com", "priyanka"),
                ("Amit Patel", "TCH003", "Database Management Systems", "9876543212", "amit.patel@school.com", "amit"),
                ("Sneha Rao", "TCH004", "Computer Networks", "9876543213", "sneha.rao@school.com", "sneha"),
                ("Vikrant Joshi", "TCH005", "Digital Electronics", "9876543214", "vikrant.joshi@school.com", "vikrant"),
            ]
            
            teachers_list = []
            teacher_users = []
            for name, emp_id, subject, phone, email, username in teachers_data:
                teachers_list.append(
                    Teacher(name=name, employee_id=emp_id, subject=subject, phone=phone, email=email)
                )
                # Create a staff user for each teacher
                User.objects.filter(username=username).delete()
                u = User.objects.create_user(username=username, email=email, password="password123")
                u.is_staff = True
                u.save()
                teacher_users.append(u)
                
            Teacher.objects.bulk_create(teachers_list)
            self.stdout.write(self.style.SUCCESS(f"Seeded {len(teachers_list)} teachers and created their user accounts."))

            # 3. Seed Students
            # Class 10-A
            students_10a = [
                "Aarav Mehta", "Ananya Iyer", "Arjun Goel", "Diya Sharma", "Ishaan Verma",
                "Kabir Kapoor", "Meera Nair", "Pranav Shah", "Riya Sen", "Rohan Joshi",
                "Siddharth Rao", "Tanya Patel", "Varun Bhatia", "Aditi Rao", "Yash Mishra"
            ]
            # Class 10-B
            students_10b = [
                "Abhishek Bose", "Bhavna Gupta", "Chaitanya Roy", "Deepika Lal", "Eshwar Reddy",
                "Gaurav Dutta", "Harini Kumar", "Indrajit Das", "Jyoti Saxena", "Karan Malhotra",
                "Mansi Chaturvedi", "Nikhil Pillai", "Prisha Dwivedi", "Rahul Deshmukh", "Sonal Jain"
            ]

            students_list = []
            
            # Seed B.Tech CSE - Section A
            for idx, name in enumerate(students_10a, start=1):
                email = f"{name.lower().replace(' ', '.')}@student.com"
                username = name.lower().replace(' ', '.')
                User.objects.filter(username=username).delete()
                u = User.objects.create_user(username=username, email=email, password="password123")
                students_list.append(
                    Student(
                        user=u,
                        name=name,
                        roll_number=idx,
                        class_name="B.Tech CSE",
                        section="A",
                        email=email,
                        phone=f"9000000{idx:03d}"
                    )
                )
            
            # Seed B.Tech ECE - Section B
            for idx, name in enumerate(students_10b, start=1):
                email = f"{name.lower().replace(' ', '.')}@student.com"
                username = name.lower().replace(' ', '.')
                User.objects.filter(username=username).delete()
                u = User.objects.create_user(username=username, email=email, password="password123")
                students_list.append(
                    Student(
                        user=u,
                        name=name,
                        roll_number=idx,
                        class_name="B.Tech ECE",
                        section="B",
                        email=email,
                        phone=f"9100000{idx:03d}"
                    )
                )

            Student.objects.bulk_create(students_list)
            self.stdout.write(self.style.SUCCESS(f"Seeded {len(students_list)} students across B.Tech CSE and ECE."))

            # Refresh students from DB
            students_db = list(Student.objects.all())

            # 4. Seed Attendance History
            # We seed history for 3 days: today - 2 days, today - 1 day, today
            today = datetime.date.today()
            dates = [today - datetime.timedelta(days=2), today - datetime.timedelta(days=1)]
            
            classes = [("B.Tech CSE", "A"), ("B.Tech ECE", "B")]

            for attendance_date in dates:
                for class_name, section in classes:
                    # Get students for this class/section
                    class_students = [s for s in students_db if s.class_name == class_name and s.section == section]
                    
                    # Randomly set status (mostly Present)
                    entries_data = {}
                    for student in class_students:
                        # 80% chance Present, 20% Absent
                        status = "Present" if random.random() > 0.20 else "Absent"
                        entries_data[student.id] = status

                    # Select a teacher randomly to mark this class
                    marking_teacher = random.choice(teacher_users)

                    # Use AttendanceService to mark it cleanly (which creates activity logs, etc.)
                    AttendanceService.mark_attendance(
                        date=attendance_date,
                        class_name=class_name,
                        section=section,
                        marked_by=marking_teacher,
                        entries_data=entries_data
                    )

            # Log seed activity
            ActivityLog.objects.create(
                activity_type="System Seeded",
                description="Database seeded with initial demo teachers, students, and history.",
                user=admin_user
            )

            self.stdout.write(self.style.SUCCESS("Database seeded successfully with sample records!"))

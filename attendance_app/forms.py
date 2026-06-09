from django import forms
from django.core.exceptions import ValidationError
from .models import Student, Teacher

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'roll_number', 'class_name', 'section', 'email', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter Full Name', 'class': 'form-input'}),
            'roll_number': forms.NumberInput(attrs={'placeholder': 'Enter Roll Number', 'class': 'form-input'}),
            'class_name': forms.TextInput(attrs={'placeholder': 'e.g., 10', 'class': 'form-input'}),
            'section': forms.TextInput(attrs={'placeholder': 'e.g., A', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'e.g., student@school.com', 'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'placeholder': 'e.g., +91 9999999999', 'class': 'form-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        roll_number = cleaned_data.get('roll_number')
        class_name = cleaned_data.get('class_name')
        section = cleaned_data.get('section')

        if roll_number and class_name and section:
            # Normalize inputs
            class_name_norm = class_name.strip()
            section_norm = section.strip()
            
            # Check unique constraint (roll_number, class_name, section)
            query = Student.objects.filter(
                roll_number=roll_number,
                class_name__iexact=class_name_norm,
                section__iexact=section_norm
            )
            
            # Exclude current instance if editing
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                error_msg = f"Roll Number {roll_number} already exists in Class {class_name_norm}-{section_norm}."
                self.add_error('roll_number', error_msg)
                raise ValidationError(error_msg)

        return cleaned_data


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['name', 'employee_id', 'subject', 'phone', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter Full Name', 'class': 'form-input'}),
            'employee_id': forms.TextInput(attrs={'placeholder': 'e.g., TCH001', 'class': 'form-input'}),
            'subject': forms.TextInput(attrs={'placeholder': 'e.g., Physics', 'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'placeholder': 'e.g., +91 9876543210', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'e.g., teacher@school.com', 'class': 'form-input'}),
        }

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id', '').strip()
        query = Teacher.objects.filter(employee_id__iexact=employee_id)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise ValidationError(f"Teacher with Employee ID '{employee_id}' already exists.")
        return employee_id

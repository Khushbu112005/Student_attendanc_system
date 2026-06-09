from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

# Custom error handlers for dark glassmorphic UI
handler404 = 'attendance_app.views.custom_404_view'
handler500 = 'attendance_app.views.custom_500_view'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('attendance_app.urls')),
]

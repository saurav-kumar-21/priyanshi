from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    
    # User Profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('me/', views.UserDetailView.as_view(), name='user-detail'),
    
    # Addresses
    path('addresses/', views.AddressListCreateView.as_view(), name='address-list'),
    path('addresses/<int:pk>/', views.AddressDetailView.as_view(), name='address-detail'),
    
    # Password Management
    path('change-password/', views.PasswordChangeView.as_view(), name='change-password'),
    path('reset-password/', views.PasswordResetView.as_view(), name='reset-password'),
    path('reset-password/confirm/', views.PasswordResetConfirmView.as_view(), name='reset-password-confirm'),
    
    # Email Verification
    path('verify-email/', views.verify_email, name='verify-email'),
    path('resend-verification/', views.resend_verification_email, name='resend-verification'),
    
    # Admin API
    path('admin/dashboard/', views.admin_dashboard_api, name='admin-dashboard-api'),
]

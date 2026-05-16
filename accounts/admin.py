from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile, Address, EmailVerification, PasswordReset

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_email_verified', 'is_active', 'created_at')
    list_filter = ('role', 'is_email_verified', 'is_active', 'is_staff', 'created_at')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone', 'date_of_birth')}),
        (_('Permissions'), {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Verification'), {'fields': ('is_email_verified', 'is_phone_verified')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'role'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'date_joined')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'location', 'timezone', 'language', 'currency', 'two_factor_enabled')
    list_filter = ('gender', 'timezone', 'language', 'currency', 'two_factor_enabled', 'receive_email_notifications')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'company', 'location')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Basic Info'), {'fields': ('user', 'avatar', 'bio', 'gender')}),
        (_('Professional'), {'fields': ('company', 'job_title', 'website')}),
        (_('Location & Preferences'), {'fields': ('location', 'timezone', 'language', 'currency')}),
        (_('Notifications'), {'fields': ('receive_email_notifications', 'receive_sms_notifications', 'two_factor_enabled')}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at')}),
    )

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'address_type', 'is_default', 'city', 'state', 'country', 'postal_code')
    list_filter = ('address_type', 'is_default', 'country', 'created_at')
    search_fields = ('user__email', 'first_name', 'last_name', 'city', 'state', 'country')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('User Info'), {'fields': ('user', 'address_type', 'is_default')}),
        (_('Name'), {'fields': ('first_name', 'last_name', 'company')}),
        (_('Address'), {'fields': ('address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country')}),
        (_('Contact'), {'fields': ('phone',)}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at')}),
    )

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'is_verified', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'created_at', 'expires_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('token', 'created_at', 'expires_at')
    
    def has_add_permission(self, request):
        return False

@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('token', 'created_at', 'expires_at')
    
    def has_add_permission(self, request):
        return False

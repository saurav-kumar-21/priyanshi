from django.contrib import admin
from .models import SiteSettings, Banner, Newsletter, ContactMessage

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'contact_email', 'commission_rate', 'created_at']
    search_fields = ['site_name', 'contact_email']
    
    def has_add_permission(self, request):
        # Only allow one instance of SiteSettings
        return not SiteSettings.objects.exists()

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'banner_type', 'is_active', 'sort_order', 'created_at']
    list_filter = ['banner_type', 'is_active', 'created_at']
    search_fields = ['title', 'subtitle', 'description']
    list_editable = ['is_active', 'sort_order']
    ordering = ['sort_order', '-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subtitle', 'description', 'image', 'banner_type')
        }),
        ('Link Settings', {
            'fields': ('link_url', 'link_text'),
            'classes': ('collapse',)
        }),
        ('Display Settings', {
            'fields': ('is_active', 'start_date', 'end_date', 'sort_order')
        }),
    )

@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ['email', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['email']
    list_editable = ['is_active']
    ordering = ['-created_at']

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    list_editable = ['is_read']
    ordering = ['-created_at']
    readonly_fields = ['name', 'email', 'subject', 'message', 'created_at']
    
    def has_add_permission(self, request):
        return False

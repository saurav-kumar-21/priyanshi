from .models import SiteSettings, Banner

def site_settings(request):
    """Global site settings context processor"""
    try:
        settings = SiteSettings.objects.first()
        if not settings:
            # Create default settings if none exist
            settings = SiteSettings.objects.create()
    except:
        settings = None
    
    # Get active banners
    try:
        banners = Banner.objects.filter(is_currently_active=True).order_by('sort_order')
    except:
        banners = Banner.objects.none()
    
    return {
        'site_settings': settings,
        'active_banners': banners,
    }

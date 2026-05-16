from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from urllib.parse import urlparse


LOCAL_DEBUG_HOSTS = {'localhost', '127.0.0.1', '::1'}


def _is_local_debug_origin(origin):
    if not origin:
        return False

    parsed = urlparse(origin)
    return parsed.scheme in {'http', 'https'} and parsed.hostname in LOCAL_DEBUG_HOSTS


class DynamicCSRFMiddleware(MiddlewareMixin):
    """
    Optional middleware to add localhost preview origins in debug mode.
    Can be disabled via ALLOW_DYNAMIC_CSRF_ORIGINS=False.
    """
    
    def process_request(self, request):
        """Add dynamic CSRF trusted origins for localhost previews only."""
        if not (settings.DEBUG and getattr(settings, 'ALLOW_DYNAMIC_CSRF_ORIGINS', False)):
            return None

        candidate_origins = set()
        origin = request.headers.get('Origin') or request.META.get('HTTP_ORIGIN', '')
        if _is_local_debug_origin(origin):
            candidate_origins.add(origin.rstrip('/'))

        host = request.get_host()
        host_origin = f"{'https' if request.is_secure() else 'http'}://{host}"
        if _is_local_debug_origin(host_origin):
            candidate_origins.add(host_origin.rstrip('/'))

        if candidate_origins:
            if not hasattr(settings, '_dynamic_csrf_origins'):
                settings._dynamic_csrf_origins = set()

            settings._dynamic_csrf_origins.update(candidate_origins)
            current_origins = set(settings.CSRF_TRUSTED_ORIGINS)
            current_origins.update(settings._dynamic_csrf_origins)
            settings.CSRF_TRUSTED_ORIGINS = sorted(current_origins)
        return None

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth import get_user_model
from core.email_notifications import send_admin_alert_email
from .models import UserProfile

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile instance when a new User is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile instance when the User is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(post_save, sender=User)
def notify_admin_when_user_registers(sender, instance, created, **kwargs):
    """Notify admin when a real storefront user account is created."""
    if not created or instance.is_superuser:
        return

    transaction.on_commit(
        lambda: send_admin_alert_email(
            f'New user registered: {instance.email}',
            'admin_new_user',
            {'user': instance},
        )
    )


@receiver(user_logged_in)
def notify_admin_when_user_logs_in(sender, request, user, **kwargs):
    """Notify admin when a storefront user logs in."""
    if user.is_superuser:
        return

    transaction.on_commit(
        lambda: send_admin_alert_email(
            f'User logged in: {user.email}',
            'admin_user_login',
            {
                'user': user,
                'ip_address': request.META.get('REMOTE_ADDR', '') if request else '',
                'user_agent': request.META.get('HTTP_USER_AGENT', '') if request else '',
            },
        )
    )


@receiver(pre_save, sender=User)
def normalize_user_email(sender, instance, **kwargs):
    """Normalize email address before saving."""
    if instance.email:
        instance.email = instance.email.lower().strip()

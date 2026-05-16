from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.email_notifications import send_admin_alert_email
from .models import ContactMessage


@receiver(post_save, sender=ContactMessage)
def notify_admin_when_contact_message_arrives(sender, instance, created, **kwargs):
    if not created:
        return

    transaction.on_commit(
        lambda: send_admin_alert_email(
            f'New contact message: {instance.subject}',
            'admin_contact_message',
            {'contact_message': instance},
        )
    )

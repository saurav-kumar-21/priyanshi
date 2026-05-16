import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from core.email_notifications import email_configuration_status, send_plain_email_result


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send a simple test email using the configured notification backend'

    def handle(self, *args, **options):
        self.stdout.write('Testing email configuration...')

        self.stdout.write('\n=== Email Configuration Status ===')
        status = email_configuration_status()
        for key, value in status.items():
            marker = 'OK' if value else 'MISSING'
            self.stdout.write(f'{marker} {key}: {value}')

        recipient = getattr(settings, 'EMAIL_HOST_USER', '')
        if not recipient:
            self.stdout.write(self.style.ERROR('No EMAIL_HOST_USER configured for testing.'))
            return

        self.stdout.write('\n=== Sending Test Email ===')
        result = send_plain_email_result(
            'Test email from Skyraa Store',
            'This is a test email to verify email configuration is working.',
            [recipient],
        )

        if result.ok:
            self.stdout.write(self.style.SUCCESS('Test email sent successfully.'))
            return

        self.stdout.write(self.style.ERROR(
            f'Test email failed: {result.error_code or "unknown_error"} - '
            f'{result.error_message or "No message was accepted by the email backend."}'
        ))

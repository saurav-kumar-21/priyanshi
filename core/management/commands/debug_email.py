import logging
import smtplib

from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check SMTP configuration and send a safe deployment test email'

    def handle(self, *args, **options):
        self.stdout.write('Email deployment diagnostics\n')

        self.stdout.write('=== Email Configuration ===')
        checks = {
            'EMAIL_BACKEND': getattr(settings, 'EMAIL_BACKEND', ''),
            'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', ''),
            'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', ''),
            'EMAIL_USE_TLS': getattr(settings, 'EMAIL_USE_TLS', ''),
            'EMAIL_USE_SSL': getattr(settings, 'EMAIL_USE_SSL', ''),
            'EMAIL_HOST_USER': 'CONFIGURED' if getattr(settings, 'EMAIL_HOST_USER', '') else '',
            'EMAIL_HOST_PASSWORD': 'CONFIGURED' if getattr(settings, 'EMAIL_HOST_PASSWORD', '') else '',
            'DEFAULT_FROM_EMAIL': 'CONFIGURED' if getattr(settings, 'DEFAULT_FROM_EMAIL', '') else '',
            'EMAIL_TIMEOUT': getattr(settings, 'EMAIL_TIMEOUT', ''),
        }

        for key, value in checks.items():
            marker = 'OK' if value not in {'', None} else 'MISSING'
            self.stdout.write(f'{marker} {key}: {value or "NOT CONFIGURED"}')

        self.stdout.write('\n=== SMTP Connection Test ===')
        try:
            connection = get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                use_tls=settings.EMAIL_USE_TLS,
                use_ssl=settings.EMAIL_USE_SSL,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
            )
            connection.open()
            connection.close()
            self.stdout.write(self.style.SUCCESS('SMTP connection successful.'))
        except smtplib.SMTPAuthenticationError as exc:
            self.stdout.write(self.style.ERROR(f'SMTP authentication failed: {exc}'))
            self.stdout.write('Use a Gmail App Password, not the normal Gmail password.')
            return
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'SMTP connection failed: {exc}'))
            logger.exception('SMTP connection failed during debug_email')
            return

        self.stdout.write('\n=== Test Email Sending ===')
        recipient = getattr(settings, 'EMAIL_HOST_USER', '')
        if not recipient:
            self.stdout.write(self.style.ERROR('No EMAIL_HOST_USER configured for testing.'))
            return

        try:
            sent_count = send_mail(
                subject='Skyraa Store email test',
                message='This is a deployment email test from Skyraa Store.',
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', recipient),
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Test email failed: {exc}'))
            logger.exception('Test email failed during debug_email')
            return

        if sent_count:
            self.stdout.write(self.style.SUCCESS('Test email sent. Check inbox and spam.'))
        else:
            self.stdout.write(self.style.ERROR('Email backend returned zero accepted messages.'))

        self.stdout.write('\n=== Deployment Checks ===')
        self.stdout.write(f'DEBUG: {getattr(settings, "DEBUG", None)}')
        self.stdout.write(f'ALLOWED_HOSTS: {", ".join(getattr(settings, "ALLOWED_HOSTS", [])) or "NOT CONFIGURED"}')
        self.stdout.write(f'FRONTEND_URL: {getattr(settings, "FRONTEND_URL", "") or "NOT CONFIGURED"}')

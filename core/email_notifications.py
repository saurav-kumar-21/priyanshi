import logging
import smtplib
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)


@dataclass
class EmailSendResult:
    sent_count: int = 0
    recipient_count: int = 0
    error_code: str = ''
    error_message: str = ''

    @property
    def ok(self):
        return self.sent_count > 0 and not self.error_code


def _site_name():
    return getattr(settings, 'SITE_NAME', '') or 'Skyraa Store'


def _site_url():
    return (getattr(settings, 'FRONTEND_URL', '') or '').rstrip('/')


def _admin_recipients():
    admin_email = (getattr(settings, 'ADMIN_EMAIL', '') or '').strip().lower()
    recipients = [admin_email] if admin_email else []

    try:
        User = get_user_model()
        recipients.extend(
            User.objects.filter(is_active=True, is_superuser=True)
            .exclude(email='')
            .values_list('email', flat=True)
        )
    except Exception:
        logger.warning('Unable to read superuser notification recipients', exc_info=True)

    if not recipients:
        try:
            from core.models import SiteSettings
            site_settings = SiteSettings.objects.first()
            contact_email = (site_settings.contact_email if site_settings else '').strip().lower()
            if contact_email:
                recipients.append(contact_email)
        except Exception:
            logger.warning('Unable to read admin notification recipient', exc_info=True)

    return sorted({email.strip().lower() for email in recipients if email and email.strip()})


def email_configuration_status():
    return {
        'host_configured': bool(getattr(settings, 'EMAIL_HOST', '')),
        'user_configured': bool(getattr(settings, 'EMAIL_HOST_USER', '')),
        'password_configured': bool(getattr(settings, 'EMAIL_HOST_PASSWORD', '')),
        'from_configured': bool(getattr(settings, 'DEFAULT_FROM_EMAIL', '')),
        'admin_configured': bool(_admin_recipients()),
    }


def _send_email_result(subject, recipients, template_name, context, *, use_bcc=False):
    try:
        recipients = sorted({email.strip().lower() for email in recipients if email and email.strip()})
        if not recipients:
            return EmailSendResult(
                error_code='no_recipients',
                error_message='No active user email recipients were found.',
            )
        if not getattr(settings, 'EMAIL_HOST_USER', '') or not getattr(settings, 'EMAIL_HOST_PASSWORD', ''):
            logger.warning('Email notification skipped because SMTP username or password is missing: %s', subject)
            return EmailSendResult(
                error_code='missing_smtp_config',
                error_message='SMTP username or password is missing in the environment.',
            )

        context = {
            **context,
            'site_name': _site_name(),
            'site_url': _site_url(),
        }
        text_body = render_to_string(f'emails/{template_name}.txt', context)
        html_body = render_to_string(f'emails/{template_name}.html', context)
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=[from_email] if use_bcc and from_email else recipients,
            bcc=recipients if use_bcc else None,
        )
        message.attach_alternative(html_body, 'text/html')

        return EmailSendResult(
            sent_count=message.send(fail_silently=False),
            recipient_count=len(recipients),
        )
    except smtplib.SMTPAuthenticationError:
        logger.error(
            'Gmail rejected EMAIL_HOST_USER/EMAIL_HOST_PASSWORD while sending: %s. '
            'Create a fresh Gmail App Password and update .env.',
            subject,
            exc_info=True
        )
        return EmailSendResult(
            error_code='smtp_auth_failed',
            error_message='Gmail rejected the SMTP username or app password.',
        )
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError):
        logger.exception('Could not connect to Gmail SMTP while sending: %s', subject)
        return EmailSendResult(
            error_code='smtp_connection_failed',
            error_message='Could not connect to Gmail SMTP. Check network and SMTP host/port.',
        )
    except Exception:
        logger.exception('Failed to send email notification: %s', subject)
        return EmailSendResult(
            error_code='send_failed',
            error_message='Email sending failed. Check server logs for details.',
        )


def _send_email(subject, recipients, template_name, context, *, use_bcc=False):
    return _send_email_result(
        subject,
        recipients,
        template_name,
        context,
        use_bcc=use_bcc,
    ).sent_count


def send_plain_email(subject, body, recipients, *, use_bcc=False):
    return _send_email(
        subject,
        recipients,
        'plain_message',
        {
            'subject': subject,
            'body': body,
        },
        use_bcc=use_bcc,
    )


def send_plain_email_result(subject, body, recipients, *, use_bcc=False):
    return _send_email_result(
        subject,
        recipients,
        'plain_message',
        {
            'subject': subject,
            'body': body,
        },
        use_bcc=use_bcc,
    )


def send_order_status_email(order):
    if not getattr(order, 'customer_email', ''):
        return 0

    status_subjects = {
        'confirmed': f'Your order {order.order_number} is confirmed',
        'cancelled': f'Your order {order.order_number} is cancelled',
    }
    subject = status_subjects.get(order.status)
    if not subject:
        return 0

    return _send_email(
        subject,
        [order.customer_email],
        'order_status',
        {
            'order': order,
            'customer_name': order.customer_name,
        },
    )


def send_new_product_email(product):
    User = get_user_model()
    recipients = (
        User.objects.filter(is_active=True)
        .exclude(Q(email='') | Q(email__isnull=True))
        .exclude(is_superuser=True)
        .exclude(profile__receive_email_notifications=False)
        .values_list('email', flat=True)
    )

    return _send_email(
        f'New arrival: {product.name}',
        recipients,
        'new_product',
        {'product': product},
        use_bcc=True,
    )


def send_admin_alert_email(subject, template_name, context):
    return _send_email(
        subject,
        _admin_recipients(),
        template_name,
        context,
    )


def send_admin_broadcast_email(subject, body):
    User = get_user_model()
    recipients = (
        User.objects.filter(is_active=True)
        .exclude(Q(email='') | Q(email__isnull=True))
        .exclude(is_superuser=True)
        .exclude(profile__receive_email_notifications=False)
        .values_list('email', flat=True)
    )

    return _send_email(
        subject,
        recipients,
        'plain_message',
        {'subject': subject, 'body': body},
        use_bcc=True,
    )


def send_admin_broadcast_email_result(subject, body):
    User = get_user_model()
    recipients = (
        User.objects.filter(is_active=True)
        .exclude(Q(email='') | Q(email__isnull=True))
        .exclude(is_superuser=True)
        .exclude(profile__receive_email_notifications=False)
        .values_list('email', flat=True)
    )

    return _send_email_result(
        subject,
        recipients,
        'plain_message',
        {'subject': subject, 'body': body},
        use_bcc=True,
    )

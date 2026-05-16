from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from accounts.models import UserProfile
from decouple import config

User = get_user_model()

class Command(BaseCommand):
    help = 'Create an admin user for the dropshipping platform'

    def handle(self, *args, **options):
        email = (getattr(settings, 'ADMIN_EMAIL', '') or '').strip().lower()
        password = getattr(settings, 'ADMIN_PASSWORD', '') or ''
        first_name = config('ADMIN_FIRST_NAME', default='Admin')
        last_name = config('ADMIN_LAST_NAME', default='User')

        if not email or not password:
            self.stdout.write(
                self.style.WARNING('Skipping admin sync: set ADMIN_EMAIL and ADMIN_PASSWORD to enable it.')
            )
            return

        admin_user = User.objects.filter(email__iexact=email).first()

        if not admin_user:
            admin_user = User.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='admin'
            )
            UserProfile.objects.get_or_create(user=admin_user)
            self.stdout.write(self.style.SUCCESS(f'Successfully created admin user: {email}'))
            self.stdout.write(self.style.WARNING('Admin password was set from environment variables.'))
            return

        update_fields = []

        if admin_user.email != email:
            admin_user.email = email
            update_fields.append('email')
        if admin_user.role != 'admin':
            admin_user.role = 'admin'
            update_fields.append('role')
        if not admin_user.is_staff:
            admin_user.is_staff = True
            update_fields.append('is_staff')
        if not admin_user.is_superuser:
            admin_user.is_superuser = True
            update_fields.append('is_superuser')
        if not admin_user.is_active:
            admin_user.is_active = True
            update_fields.append('is_active')
        if not admin_user.first_name:
            admin_user.first_name = first_name
            update_fields.append('first_name')
        if not admin_user.last_name:
            admin_user.last_name = last_name
            update_fields.append('last_name')
        if not admin_user.check_password(password):
            admin_user.set_password(password)
            update_fields.append('password')

        if update_fields:
            admin_user.save(update_fields=update_fields)

        UserProfile.objects.get_or_create(user=admin_user)
        self.stdout.write(self.style.SUCCESS(f'Admin user synced successfully: {email}'))

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
import uuid

class User(AbstractUser):
    ROLE_CHOICES = (
        ('customer', _('Customer')),
        ('seller', _('Seller')),
        ('admin', _('Admin')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    phone = PhoneNumberField(_('phone number'), blank=True, null=True)
    role = models.CharField(_('role'), max_length=20, choices=ROLE_CHOICES, default='customer')
    is_email_verified = models.BooleanField(_('email verified'), default=False)
    is_phone_verified = models.BooleanField(_('phone verified'), default=False)
    date_of_birth = models.DateField(_('date of birth'), blank=True, null=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        
        email = self.normalize_email(email).strip().lower()
        if not extra_fields.get('username'):
            if len(email) <= 150:
                extra_fields['username'] = email
            else:
                import hashlib
                email_hash = hashlib.md5(email.encode('utf-8')).hexdigest()
                extra_fields['username'] = f"{email[:117]}-{email_hash}"
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

# Add custom manager to User model
User.add_to_class('objects', UserManager())

class UserProfile(models.Model):
    GENDER_CHOICES = (
        ('M', _('Male')),
        ('F', _('Female')),
        ('O', _('Other')),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(_('avatar'), upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(_('bio'), max_length=500, blank=True)
    gender = models.CharField(_('gender'), max_length=1, choices=GENDER_CHOICES, blank=True)
    website = models.URLField(_('website'), blank=True)
    company = models.CharField(_('company'), max_length=100, blank=True)
    job_title = models.CharField(_('job title'), max_length=100, blank=True)
    location = models.CharField(_('location'), max_length=100, blank=True)
    timezone = models.CharField(_('timezone'), max_length=50, default='UTC')
    language = models.CharField(_('language'), max_length=10, default='en')
    currency = models.CharField(_('currency'), max_length=3, default='INR')
    receive_email_notifications = models.BooleanField(_('receive email notifications'), default=True)
    receive_sms_notifications = models.BooleanField(_('receive sms notifications'), default=False)
    two_factor_enabled = models.BooleanField(_('two factor enabled'), default=False)
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
        
    def __str__(self):
        return f"{self.user.email} Profile"

class Address(models.Model):
    ADDRESS_TYPE_CHOICES = (
        ('home', _('Home')),
        ('work', _('Work')),
        ('other', _('Other')),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(_('address type'), max_length=10, choices=ADDRESS_TYPE_CHOICES, default='home')
    is_default = models.BooleanField(_('default address'), default=False)
    first_name = models.CharField(_('first name'), max_length=50)
    last_name = models.CharField(_('last name'), max_length=50)
    company = models.CharField(_('company'), max_length=100, blank=True)
    address_line_1 = models.CharField(_('address line 1'), max_length=255)
    address_line_2 = models.CharField(_('address line 2'), max_length=255, blank=True)
    city = models.CharField(_('city'), max_length=100)
    state = models.CharField(_('state'), max_length=100)
    postal_code = models.CharField(_('postal code'), max_length=20)
    country = models.CharField(_('country'), max_length=100)
    phone = PhoneNumberField(_('phone'), blank=True, null=True)
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Address')
        verbose_name_plural = _('Addresses')
        ordering = ['-is_default', '-created_at']
        
    def __str__(self):
        return f"{self.user.email} - {self.address_type}"
    
    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    token = models.UUIDField(_('token'), default=uuid.uuid4, editable=False)
    is_verified = models.BooleanField(_('verified'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    expires_at = models.DateTimeField(_('expires at'))
    
    class Meta:
        verbose_name = _('Email Verification')
        verbose_name_plural = _('Email Verifications')
        
    def __str__(self):
        return f"{self.user.email} - {self.token}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

class PasswordReset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_resets')
    token = models.UUIDField(_('token'), default=uuid.uuid4, editable=False)
    is_used = models.BooleanField(_('used'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    expires_at = models.DateTimeField(_('expires at'))
    
    class Meta:
        verbose_name = _('Password Reset')
        verbose_name_plural = _('Password Resets')
        
    def __str__(self):
        return f"{self.user.email} - {self.token}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

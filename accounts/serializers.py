from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import re
from .models import User, UserProfile, Address


def normalize_phone_number(raw_phone, country_hint=''):
    if raw_phone is None:
        return None

    if not isinstance(raw_phone, str):
        return raw_phone

    phone = raw_phone.strip()
    if not phone:
        return None

    if phone.startswith('+'):
        digits = re.sub(r'\D', '', phone)
        return f"+{digits}" if digits else phone

    digits = re.sub(r'\D', '', phone)
    if not digits:
        return phone

    country = (country_hint or '').strip().lower()
    if len(digits) == 10:
        if country in {'india', 'in'}:
            return f"+91{digits}"
        if country in {'united states', 'united states of america', 'usa', 'us'}:
            return f"+1{digits}"
        return f"+1{digits}"

    if len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"

    if 8 <= len(digits) <= 15:
        return f"+{digits}"

    return phone


def _sync_env_admin_user(login_email, login_password):
    if not getattr(settings, 'ALLOW_ENV_ADMIN_SYNC', False):
        return None

    admin_email = (getattr(settings, 'ADMIN_EMAIL', '') or '').strip().lower()
    admin_password = getattr(settings, 'ADMIN_PASSWORD', '') or ''

    if not admin_email or not admin_password:
        return None

    if login_email != admin_email or login_password != admin_password:
        return None

    user = User.objects.filter(email__iexact=admin_email).first()
    if not user:
        return User.objects.create_superuser(
            email=admin_email,
            password=admin_password,
            first_name='Admin',
            last_name='User',
            role='admin',
            is_active=True,
        )

    update_fields = []

    if user.email != admin_email:
        user.email = admin_email
        update_fields.append('email')
    if user.role != 'admin':
        user.role = 'admin'
        update_fields.append('role')
    if not user.is_staff:
        user.is_staff = True
        update_fields.append('is_staff')
    if not user.is_superuser:
        user.is_superuser = True
        update_fields.append('is_superuser')
    if not user.is_active:
        user.is_active = True
        update_fields.append('is_active')
    if not user.first_name:
        user.first_name = 'Admin'
        update_fields.append('first_name')
    if not user.last_name:
        user.last_name = 'User'
        update_fields.append('last_name')
    if not user.check_password(admin_password):
        user.set_password(admin_password)
        update_fields.append('password')

    if update_fields:
        user.save(update_fields=update_fields)

    return user


class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'password_confirm', 'phone', 'date_of_birth')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    @staticmethod
    def _normalize_phone_number(phone):
        phone = phone.strip()
        if not phone:
            return None

        if phone.startswith('+'):
            digits = re.sub(r'\D', '', phone)
            return f"+{digits}" if digits else phone

        digits = re.sub(r'\D', '', phone)
        if not digits:
            return phone

        # Support common local US formats such as 9876543210.
        if len(digits) == 10:
            return f"+1{digits}"
        if len(digits) == 11 and digits.startswith('1'):
            return f"+{digits}"

        # If user entered an international number without +, normalize to E.164.
        if 8 <= len(digits) <= 15:
            return f"+{digits}"

        return phone

    def to_internal_value(self, data):
        # Frontend sends optional date as empty string when left blank.
        normalized_data = data.copy()
        if isinstance(normalized_data.get('email'), str):
            normalized_data['email'] = normalized_data['email'].strip().lower()
        if normalized_data.get('date_of_birth') == '':
            normalized_data['date_of_birth'] = None
        if isinstance(normalized_data.get('phone'), str):
            normalized_data['phone'] = self._normalize_phone_number(normalized_data['phone'])
        return super().to_internal_value(normalized_data)

    def validate_email(self, value):
        email = (value or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(_('A user with this email already exists.'))
        if User.objects.filter(username__iexact=email).exists():
            raise serializers.ValidationError(_('A user with this email already exists.'))
        return email
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(_("Passwords don't match."))
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        
        # Use UserManager's create_user method
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone'),
            date_of_birth=validated_data.get('date_of_birth'),
        )
        
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = (attrs.get('email') or '').strip().lower()
        password = attrs.get('password')
        
        if email and password:
            existing_user = User.objects.filter(email__iexact=email).first()
            auth_username = existing_user.email if existing_user else email
            user = authenticate(request=self.context.get('request'),
                              username=auth_username, password=password)

            if not user:
                _sync_env_admin_user(email, password)
                user = authenticate(
                    request=self.context.get('request'),
                    username=auth_username,
                    password=password,
                )
            
            if not user:
                raise serializers.ValidationError(_('Invalid credentials.'))
            
            if not user.is_active:
                raise serializers.ValidationError(_('User account is disabled.'))
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(_('Must include email and password.'))

class UserProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    user_created_at = serializers.DateTimeField(source='user.created_at', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'full_name', 'phone', 
                 'role', 'is_email_verified', 'is_phone_verified', 'date_of_birth',
                 'profile', 'created_at', 'updated_at')
        read_only_fields = (
            'id',
            'email',
            'role',
            'is_email_verified',
            'is_phone_verified',
            'created_at',
            'updated_at',
        )

    def to_internal_value(self, data):
        normalized_data = data.copy()
        if isinstance(normalized_data.get('phone'), str):
            normalized_data['phone'] = normalize_phone_number(normalized_data.get('phone'))
        return super().to_internal_value(normalized_data)

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')

    def to_internal_value(self, data):
        normalized_data = data.copy()
        if isinstance(normalized_data.get('phone'), str):
            normalized_data['phone'] = normalize_phone_number(
                normalized_data.get('phone'),
                country_hint=normalized_data.get('country', '')
            )
        return super().to_internal_value(normalized_data)
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        if not user.addresses.exists():
            validated_data['is_default'] = True
        return super().create(validated_data)

class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_('Current password is incorrect.'))
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(_("New passwords don't match."))
        return attrs
    
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        return value.lower()

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(_("Passwords don't match."))
        return attrs

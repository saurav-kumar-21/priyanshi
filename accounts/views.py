from django.shortcuts import render, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Count, Q
from .models import User, UserProfile, Address, EmailVerification, PasswordReset
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    UserProfileSerializer, AddressSerializer, PasswordChangeSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer
)
import uuid
import logging
import time
from core.email_notifications import send_plain_email_result


logger = logging.getLogger(__name__)


def _send_mail_safely(subject, message, recipients, *, log_context='email dispatch', retries=1):
    """
    Send mail inline for reliability and retry once on transient SMTP failures.
    Returns True when at least one message is accepted by the backend.
    """
    email_host = getattr(settings, 'EMAIL_HOST_USER', '')
    email_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    
    logger.info(f'Email config check for {log_context}:')
    logger.info(f'  EMAIL_HOST: {getattr(settings, "EMAIL_HOST", "NOT SET")}')
    logger.info(f'  EMAIL_PORT: {getattr(settings, "EMAIL_PORT", "NOT SET")}')
    logger.info(f'  EMAIL_USE_TLS: {getattr(settings, "EMAIL_USE_TLS", "NOT SET")}')
    logger.info(f'  EMAIL_HOST_USER configured: {bool(email_host)}')
    logger.info(f'  EMAIL_HOST_PASSWORD configured: {bool(email_password)}')
    logger.info(f'  DEFAULT_FROM_EMAIL: {getattr(settings, "DEFAULT_FROM_EMAIL", "NOT SET")}')
    
    if not email_host or not email_password:
        logger.error('%s skipped because SMTP username or password is missing', log_context)
        return False

    for attempt in range(retries + 1):
        try:
            result = send_plain_email_result(subject, message, recipients)
            if result.ok:
                return True
            logger.warning(
                '%s failed with %s: %s',
                log_context,
                result.error_code or 'no_accepted_recipients',
                result.error_message or 'No accepted recipients',
            )
        except Exception:
            logger.warning(
                '%s failed (attempt %s/%s)',
                log_context,
                attempt + 1,
                retries + 1,
                exc_info=True
            )

        if attempt < retries:
            time.sleep(1)

    return False


def _otp_to_uuid(otp):
    otp_str = str(otp).strip()
    if not otp_str.isdigit() or len(otp_str) != 6:
        raise ValueError('OTP must be a 6-digit number')
    return uuid.UUID(f"00000000-0000-0000-0000-000000{otp_str}")


def _serializer_errors_to_messages(errors):
    messages = []
    for field, field_errors in errors.items():
        label = field.replace('_', ' ').title()
        for error in field_errors:
            messages.append(f"{label}: {error}")
    return messages

# Admin API Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_dashboard_api(request):
    """Get admin dashboard statistics"""
    if not request.user.is_superuser:
        return Response({'error': _('Admin access required.')}, status=status.HTTP_403_FORBIDDEN)

    try:
        # User statistics
        total_users = User.objects.filter(role='user').count()
        total_sellers = User.objects.filter(role='seller').count()
        total_admins = User.objects.filter(role='admin').count()
        
        # Seller statistics
        from sellers.models import Seller
        pending_sellers = Seller.objects.filter(approval_status='pending').count()
        approved_sellers = Seller.objects.filter(approval_status='approved').count()
        
        # Product statistics
        from products.models import Product
        total_products = Product.objects.count()
        active_products = Product.objects.filter(status='active').count()
        
        # Order statistics
        from orders.models import Order
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(status='pending').count()
        delivered_orders = Order.objects.filter(status='delivered').count()
        
        # Recent activities (mock data for now)
        recent_activities = []
        
        return Response({
            'users': {
                'total': total_users,
                'sellers': total_sellers,
                'admins': total_admins
            },
            'sellers': {
                'total': total_sellers,
                'pending': pending_sellers,
                'approved': approved_sellers
            },
            'products': {
                'total': total_products,
                'active': active_products
            },
            'orders': {
                'total': total_orders,
                'pending': pending_orders,
                'delivered': delivered_orders
            },
            'recent_activities': recent_activities
        })
    except Exception:
        logger.exception('Failed to load admin dashboard stats')
        return Response({'error': _('Unable to load dashboard data.')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'errors': serializer.errors,
                'error_messages': _serializer_errors_to_messages(serializer.errors)
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = serializer.save()
        except Exception:
            logger.exception('User registration failed while creating account')
            return Response({
                'error': _('Unable to complete registration right now. Please try again.'),
            }, status=status.HTTP_400_BAD_REQUEST)

        refresh = None
        try:
            refresh = RefreshToken.for_user(user)
        except Exception:
            logger.warning('JWT generation failed after registration', exc_info=True)

        verification_email_sent = self.send_verification_email(user)
        success_message = _(
            'Registration successful. Please check your email for OTP verification.'
            if verification_email_sent
            else 'Registration successful, but OTP email could not be sent right now. Please use Resend OTP.'
        )

        try:
            user_data = UserSerializer(user).data
        except Exception:
            logger.warning('User serialization failed after registration', exc_info=True)
            user_data = {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'is_email_verified': user.is_email_verified,
            }

        response_data = {
            'user': user_data,
            'verification_email_sent': verification_email_sent,
            'message': success_message,
        }
        if refresh is not None:
            response_data.update({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })

        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def send_verification_email(self, user):
        """Send OTP verification email to user"""
        try:
            import random
            import string
            
            # Generate 6-digit OTP
            otp = ''.join(random.choices(string.digits, k=6))
            otp_token = _otp_to_uuid(otp)
            
            # Save or update OTP
            EmailVerification.objects.filter(user=user, is_verified=False).delete()
            EmailVerification.objects.create(
                user=user,
                token=otp_token,
                expires_at=timezone.now() + timedelta(hours=1),
                is_verified=False,
            )
            
            subject = _('Verify your email address')
            message = _(
                f'Hello {user.first_name},\n\n'
                f'Your OTP for email verification is: {otp}\n\n'
                f'This OTP will expire in 1 hour.\n\n'
                f'Please enter this OTP on the verification page.\n\n'
                f'Thank you!'
            )

            return _send_mail_safely(
                subject,
                message,
                [user.email],
                log_context='Verification OTP email dispatch'
            )
        except Exception:
            # Do not fail registration if mail provider has transient issues.
            logger.warning('Failed to send verification OTP email', exc_info=True)
            return False

class UserLoginView(generics.GenericAPIView):
    """User login endpoint"""
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        login(request, user)
        
        # Check if user is admin and redirect accordingly
        from django.conf import settings
        admin_email = (getattr(settings, 'ADMIN_EMAIL', '') or '').strip().lower()
        
        response_data = {
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': _('Login successful.')
        }
        
        # Add redirect URL for admin users
        if user.is_superuser or (user.email or '').strip().lower() == admin_email:
            response_data['redirect_url'] = '/admin-panel/'
        else:
            response_data['redirect_url'] = '/'
        
        return Response(response_data)

class UserLogoutView(generics.GenericAPIView):
    """User logout endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        logout(request)

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                logger.warning('Refresh token blacklist failed during logout', exc_info=True)

        return Response({'message': _('Logout successful.')})

class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

class UserDetailView(generics.RetrieveUpdateAPIView):
    """Get and update user details"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class AddressListCreateView(generics.ListCreateAPIView):
    """List and create addresses"""
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update and delete address"""
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

class PasswordChangeView(generics.GenericAPIView):
    """Change user password"""
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': _('Password changed successfully.')})

class PasswordResetView(generics.GenericAPIView):
    """Request password reset"""
    serializer_class = PasswordResetSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email'].lower()
        user = User.objects.filter(email__iexact=email).first()

        # Always return success-style response to avoid account enumeration.
        if user:
            try:
                expires_at = timezone.now() + timedelta(hours=1)
                password_reset = PasswordReset.objects.create(
                    user=user,
                    expires_at=expires_at
                )

                reset_url = f"{settings.FRONTEND_URL}/reset-password/{password_reset.token}/"
                subject = _('Reset your password')
                message = _(
                    f'Hello {user.first_name},\n\n'
                    f'Please click the link below to reset your password:\n'
                    f'{reset_url}\n\n'
                    f'This link will expire in 1 hour.\n\n'
                    f'Thank you!'
                )
                _send_mail_safely(
                    subject,
                    message,
                    [user.email],
                    log_context='Password reset email dispatch'
                )
            except Exception:
                logger.warning('Password reset email dispatch failed', exc_info=True)

        return Response({
            'message': _('Password reset link sent to your email.')
        })

class PasswordResetConfirmView(generics.GenericAPIView):
    """Confirm password reset"""
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            password_reset = PasswordReset.objects.get(
                token=token,
                is_used=False,
                expires_at__gt=timezone.now()
            )
            
            # Update user password
            user = password_reset.user
            user.set_password(new_password)
            user.save()
            
            # Mark password reset as used
            password_reset.is_used = True
            password_reset.save()
            
            return Response({'message': _('Password reset successful.')})
            
        except PasswordReset.DoesNotExist:
            return Response(
                {'error': _('Invalid or expired reset token.')},
                status=status.HTTP_400_BAD_REQUEST
            )

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_email(request):
    """Verify email address using OTP"""
    try:
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        if not email or not otp:
            return Response({'error': 'Email and OTP are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find user by email
        user = User.objects.filter(email=email.lower()).first()
        if not user:
            return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            otp_token = _otp_to_uuid(otp)
        except ValueError:
            return Response({'error': 'OTP must be a valid 6-digit code'}, status=status.HTTP_400_BAD_REQUEST)

        # Find email verification record
        email_verification = EmailVerification.objects.filter(
            user=user,
            token=otp_token,
            is_verified=False,
            expires_at__gt=timezone.now()
        ).first()
        
        if not email_verification:
            return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark email as verified
        user.is_email_verified = True
        user.save()
        
        email_verification.is_verified = True
        email_verification.save()
        
        # Generate JWT tokens and log the user in
        refresh = RefreshToken.for_user(user)
        login(request, user)
        
        # Determine redirect URL based on user role
        from django.conf import settings
        admin_email = (getattr(settings, 'ADMIN_EMAIL', '') or '').strip().lower()
        
        redirect_url = '/profile/'
        if user.is_superuser or (user.email or '').strip().lower() == admin_email:
            redirect_url = '/admin-panel/'
        
        return Response({
            'message': 'Email verified successfully!',
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'redirect_url': redirect_url
        })
        
    except Exception:
        logger.exception('Email verification failed')
        return Response({'error': _('Unable to verify email right now.')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def resend_verification_email(request):
    """Resend email verification"""
    email = request.data.get('email')
    generic_message = _('If the email exists and is unverified, a verification OTP has been sent.')

    if not email and request.user.is_authenticated:
        email = request.user.email

    if not email:
        return Response(
            {'error': _('Email is required.')},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.filter(email=email.lower()).first()
    if not user or user.is_email_verified:
        return Response({'message': generic_message})

    # Delete existing unverified tokens
    EmailVerification.objects.filter(user=user, is_verified=False).delete()

    # Create new 6-digit OTP token
    import random
    import string
    otp = ''.join(random.choices(string.digits, k=6))
    otp_token = _otp_to_uuid(otp)

    expires_at = timezone.now() + timedelta(hours=1)
    EmailVerification.objects.create(
        user=user,
        token=otp_token,
        expires_at=expires_at
    )

    # Send verification email with OTP
    subject = _('Verify your email address')
    message = _(
        f'Hello {user.first_name},\n\n'
        f'Your OTP for email verification is: {otp}\n\n'
        f'This OTP will expire in 1 hour.\n\n'
        f'Please enter this OTP on the verification page.\n\n'
        f'Thank you!'
    )
    _send_mail_safely(
        subject,
        message,
        [user.email],
        log_context='Resend verification OTP email dispatch'
    )

    return Response({'message': generic_message})


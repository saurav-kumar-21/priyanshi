from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from datetime import datetime
from accounts.models import User
from sellers.models import Seller
from orders.models import Order
from orders.serializers import OrderDetailSerializer
from .serializers import UserSerializer
from products.models import Category


def _require_admin(request):
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    return None


def _serialize_seller(seller):
    return {
        'id': str(seller.id),
        'business_name': seller.business_name,
        'business_description': seller.business_description,
        'business_type': seller.business_type,
        'registration_number': seller.registration_number,
        'tax_id': seller.tax_id,
        'business_email': seller.business_email,
        'business_phone': seller.business_phone,
        'business_website': seller.business_website,
        'business_address': seller.business_address,
        'business_city': seller.business_city,
        'business_state': seller.business_state,
        'business_country': seller.business_country,
        'business_postal_code': seller.business_postal_code,
        'approval_status': seller.approval_status,
        'rejection_reason': seller.rejection_reason,
        'approved_at': seller.approved_at,
        'approved_by': seller.approved_by.email if seller.approved_by else None,
        'bank_account_name': seller.bank_account_name,
        'bank_account_number': seller.bank_account_number,
        'bank_name': seller.bank_name,
        'bank_branch': seller.bank_branch,
        'ifsc_code': seller.ifsc_code,
        'total_sales': seller.total_sales,
        'total_orders': seller.total_orders,
        'average_rating': seller.average_rating,
        'total_reviews': seller.total_reviews,
        'commission_rate': seller.commission_rate,
        'created_at': seller.created_at,
        'updated_at': seller.updated_at,
        'user': {
            'id': str(seller.user.id),
            'first_name': seller.user.first_name,
            'last_name': seller.user.last_name,
            'full_name': seller.user.full_name,
            'email': seller.user.email,
            'phone': str(seller.user.phone) if seller.user.phone else '',
        },
    }


def _parse_datetime_input(value):
    if not value:
        return None

    parsed = parse_datetime(value)
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed


def _build_unique_category_slug(name, *, exclude_id=None):
    base_slug = slugify(name) or 'category'
    slug = base_slug
    queryset = Category.objects.all()
    if exclude_id is not None:
        queryset = queryset.exclude(id=exclude_id)

    counter = 1
    while queryset.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1

    return slug

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_user_detail(request, user_id):
    """Get user details for admin"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    user = get_object_or_404(User, id=user_id)
    serializer = UserSerializer(user)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_toggle_user_status(request, user_id):
    """Toggle user active status"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    
    return Response({
        'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
        'is_active': user.is_active
    })

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def admin_delete_user(request, user_id):
    """Delete user"""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    user = get_object_or_404(User, id=user_id)
    user.delete()
    
    return Response({'message': 'User deleted successfully'})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_approve_seller(request, seller_id):
    """Approve a seller"""
    admin_error = _require_admin(request)
    if admin_error:
        return admin_error
    
    try:
        seller = Seller.objects.get(id=seller_id)
        seller.approval_status = 'approved'
        seller.rejection_reason = ''
        seller.approved_by = request.user
        seller.approved_at = timezone.now()
        seller.save()
        
        return Response({'message': 'Seller approved successfully', 'seller': _serialize_seller(seller)})
    except Seller.DoesNotExist:
        return Response({'error': 'Seller not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_seller_detail(request, seller_id):
    """Get seller detail for admin panel."""
    admin_error = _require_admin(request)
    if admin_error:
        return admin_error

    seller = get_object_or_404(Seller.objects.select_related('user', 'approved_by'), id=seller_id)
    return Response(_serialize_seller(seller))


@api_view(['PATCH', 'POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def admin_edit_seller(request, seller_id):
    """Edit seller profile details from admin panel."""
    admin_error = _require_admin(request)
    if admin_error:
        return admin_error

    seller = get_object_or_404(Seller.objects.select_related('user'), id=seller_id)

    editable_fields = [
        'business_name', 'business_description', 'business_type', 'registration_number', 'tax_id',
        'business_email', 'business_phone', 'business_website', 'business_address', 'business_city',
        'business_state', 'business_country', 'business_postal_code', 'bank_account_name',
        'bank_account_number', 'bank_name', 'bank_branch', 'ifsc_code', 'commission_rate',
    ]

    for field in editable_fields:
        if field in request.data:
            setattr(seller, field, request.data.get(field))

    owner_first_name = request.data.get('owner_first_name')
    owner_last_name = request.data.get('owner_last_name')
    owner_phone = request.data.get('owner_phone')

    user_changed = False
    if owner_first_name is not None:
        seller.user.first_name = owner_first_name
        user_changed = True
    if owner_last_name is not None:
        seller.user.last_name = owner_last_name
        user_changed = True
    if owner_phone is not None:
        seller.user.phone = owner_phone
        user_changed = True

    if user_changed:
        seller.user.save(update_fields=['first_name', 'last_name', 'phone', 'updated_at'])

    seller.save()
    return Response({'message': 'Seller details updated successfully', 'seller': _serialize_seller(seller)})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_reject_seller(request, seller_id):
    """Reject seller application."""
    admin_error = _require_admin(request)
    if admin_error:
        return admin_error

    seller = get_object_or_404(Seller, id=seller_id)
    rejection_reason = (request.data.get('rejection_reason') or request.data.get('reason') or '').strip()
    seller.approval_status = 'rejected'
    seller.rejection_reason = rejection_reason or 'Seller application rejected by admin.'
    seller.approved_by = request.user
    seller.approved_at = timezone.now()
    seller.save(update_fields=['approval_status', 'rejection_reason', 'approved_by', 'approved_at', 'updated_at'])

    return Response({'message': 'Seller rejected successfully', 'seller': _serialize_seller(seller)})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_suspend_seller(request, seller_id):
    """Suspend an approved seller."""
    admin_error = _require_admin(request)
    if admin_error:
        return admin_error

    seller = get_object_or_404(Seller, id=seller_id)
    seller.approval_status = 'suspended'
    seller.approved_by = request.user
    seller.save(update_fields=['approval_status', 'approved_by', 'updated_at'])

    return Response({'message': 'Seller suspended successfully', 'seller': _serialize_seller(seller)})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_reactivate_seller(request, seller_id):
    """Reactivate suspended or rejected seller."""
    admin_error = _require_admin(request)
    if admin_error:
        return admin_error

    seller = get_object_or_404(Seller, id=seller_id)
    seller.approval_status = 'approved'
    seller.rejection_reason = ''
    seller.approved_by = request.user
    seller.approved_at = timezone.now()
    seller.save(update_fields=['approval_status', 'rejection_reason', 'approved_by', 'approved_at', 'updated_at'])

    return Response({'message': 'Seller reactivated successfully', 'seller': _serialize_seller(seller)})


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def admin_delete_seller(request, seller_id):
    """Delete seller account and linked user."""
    admin_error = _require_admin(request)
    if admin_error:
        return admin_error

    seller = get_object_or_404(Seller.objects.select_related('user'), id=seller_id)
    seller_user = seller.user
    seller_user.delete()

    return Response({'message': 'Seller deleted successfully'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_order_detail(request, order_id):
    """Get order details for admin panel."""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    order = get_object_or_404(
        Order.objects.select_related('user', 'approved_by').prefetch_related('items__product__images'),
        id=order_id
    )
    serializer = OrderDetailSerializer(order, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def admin_update_order_status(request, order_id):
    """Approve or disapprove order from admin panel."""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    order = get_object_or_404(Order, id=order_id)
    action = (request.data.get('action') or '').strip().lower()
    admin_notes = (request.data.get('admin_notes') or '').strip()
    cancellation_reason = (request.data.get('cancellation_reason') or '').strip()
    verification_outcome = (request.data.get('verification_outcome') or '').strip().lower()
    estimated_delivery_at_raw = (
        request.data.get('estimated_delivery_at')
        or request.data.get('estimated_delivery_datetime')
        or ''
    ).strip()
    estimated_delivery_at = _parse_datetime_input(estimated_delivery_at_raw) if estimated_delivery_at_raw else None
    refund_processed_at_raw = (request.data.get('refund_processed_at') or '').strip()
    refund_processed_at = _parse_datetime_input(refund_processed_at_raw) if refund_processed_at_raw else None
    refund_screenshot = request.FILES.get('refund_screenshot')

    if action not in ['approve', 'cancel', 'disapprove', 'approve_cancel_request', 'reject_cancel_request']:
        return Response(
            {'error': 'Invalid action. Use approve, disapprove, approve_cancel_request, or reject_cancel_request.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if action == 'approve':
        if order.status != 'pending':
            return Response({'error': 'Only pending orders can be approved.'}, status=status.HTTP_400_BAD_REQUEST)
        if not estimated_delivery_at_raw:
            return Response(
                {'error': 'Delivery date and time is required to approve an order.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not estimated_delivery_at:
            return Response(
                {'error': 'Invalid delivery date and time format.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        delivery_display = timezone.localtime(estimated_delivery_at).strftime('%d %b %Y %I:%M %p')
        order.status = 'confirmed'
        order.payment_status = 'paid'
        order.approved_at = timezone.now()
        order.approved_by = request.user
        order.estimated_delivery_date = timezone.localtime(estimated_delivery_at).date()
        order.status_message = f'Order approved by admin. Expected delivery on {delivery_display}.'
        order.cancellation_reason = ''
        order.refund_processed_at = None
        order.refund_screenshot = None
        if order.cancellation_request_status == 'pending':
            order.cancellation_request_status = 'rejected'
        message = 'Order approved successfully with delivery schedule.'
    elif action in ['cancel', 'disapprove']:
        previous_order_status = order.status
        if previous_order_status not in ['pending', 'confirmed']:
            return Response({'error': 'Only pending or confirmed orders can be disapproved.'}, status=status.HTTP_400_BAD_REQUEST)
        if not cancellation_reason:
            return Response(
                {'error': 'Disapprove reason is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'cancelled'
        order.estimated_delivery_date = None
        refund_number = order.payment_phone_number or order.recipient_phone or 'the payment number'
        reason_for_message = cancellation_reason.rstrip('.') or cancellation_reason
        if previous_order_status == 'pending':
            if verification_outcome not in ['refunded', 'not_verified']:
                return Response(
                    {'error': 'Please choose whether the order is refunded or payment not verified.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if verification_outcome == 'not_verified':
                order.payment_status = 'failed'
                order.status_message = (
                    f'Order disapproved by admin. Reason: {reason_for_message}. '
                    'Payment could not be verified.'
                )
            else:
                order.payment_status = 'refunded'
                order.status_message = (
                    f'Order disapproved by admin. Reason: {reason_for_message}. '
                    f'If payment was submitted, refund will be sent to {refund_number}.'
                )
        else:
            order.payment_status = 'refunded'
            order.status_message = (
                f'Order disapproved by admin. Reason: {reason_for_message}. '
                f'If payment was submitted, refund will be sent to {refund_number}.'
            )
        order.cancellation_reason = cancellation_reason
        if order.cancellation_request_status == 'pending':
            order.cancellation_request_status = 'approved'

        # Return quantities to stock when an order is canceled.
        for item in order.items.select_related('product'):
            if item.product.track_inventory:
                item.product.quantity = item.product.quantity + item.quantity
                item.product.save(update_fields=['quantity', 'updated_at'])
        message = (
            'Order cancelled. Payment marked as not verified.'
            if verification_outcome == 'not_verified'
            else 'Order disapproved successfully.'
        )
    elif action == 'approve_cancel_request':
        if order.cancellation_request_status != 'pending':
            return Response(
                {'error': 'No pending cancellation request found for this order.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if order.status in ['cancelled', 'delivered']:
            return Response(
                {'error': 'This order cannot be canceled now.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not refund_screenshot:
            return Response(
                {'error': 'Refund screenshot is required to approve cancellation request.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not refund_processed_at_raw:
            return Response(
                {'error': 'Refund date and time is required to approve cancellation request.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not refund_processed_at:
            return Response(
                {'error': 'Invalid refund date and time format.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'cancelled'
        order.payment_status = 'refunded'
        order.cancellation_request_status = 'approved'
        order.cancellation_reason = order.cancellation_request_reason or cancellation_reason or 'Canceled on customer request.'
        order.refund_screenshot = refund_screenshot
        order.refund_processed_at = refund_processed_at
        refund_number = order.payment_phone_number or order.recipient_phone or 'the payment number'
        refund_time_display = timezone.localtime(refund_processed_at).strftime('%d %b %Y %I:%M %p')
        order.status_message = (
            'Your cancellation request is approved. '
            f'Refund sent to {refund_number} on {refund_time_display}.'
        )

        for item in order.items.select_related('product'):
            if item.product.track_inventory:
                item.product.quantity = item.product.quantity + item.quantity
                item.product.save(update_fields=['quantity', 'updated_at'])

        message = 'Cancellation request approved and refund marked.'
    else:
        if order.cancellation_request_status != 'pending':
            return Response(
                {'error': 'No pending cancellation request found for this order.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.cancellation_request_status = 'rejected'
        order.status_message = 'Your cancellation request was rejected by admin.'
        if cancellation_reason:
            order.admin_notes = cancellation_reason
        message = 'Cancellation request rejected.'

    if admin_notes:
        order.admin_notes = admin_notes

    order.save()

    return Response({
        'success': True,
        'message': message,
        'status': order.status,
        'payment_status': order.payment_status,
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def admin_delete_cancelled_orders(request):
    """Delete all cancelled orders from admin dashboard."""
    if not request.user.is_superuser:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    cancelled_orders = Order.objects.filter(status='cancelled')
    deleted_count = cancelled_orders.count()
    cancelled_orders.delete()

    return Response({
        'success': True,
        'message': f'{deleted_count} cancelled order(s) deleted successfully.',
        'deleted_count': deleted_count,
    })


# Category Management API Views
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def admin_category_list(request):
    """Get list of all categories"""
    categories = Category.objects.all().order_by('name')
    data = []
    for category in categories:
        # Count products in this category
        from products.models import Product
        product_count = Product.objects.filter(category=category).count()
        
        # Count subcategories
        subcategory_count = Category.objects.filter(parent=category).count()
        
        category_data = {
            'id': str(category.id),
            'name': category.name,
            'description': category.description,
            'image': category.image.url if category.image else None,
            'product_count': product_count,
            'subcategory_count': subcategory_count,
            'created_at': category.created_at.isoformat(),
            'updated_at': category.updated_at.isoformat(),
        }
        data.append(category_data)
    
    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def admin_create_category(request):
    """Create a new category"""
    if not request.user.is_superuser:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    name = request.data.get('name', '').strip()
    description = request.data.get('description', '').strip()
    image = request.FILES.get('image')
    
    if not name:
        return Response({'error': 'Category name is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if category with this name already exists
    if Category.objects.filter(name__iexact=name).exists():
        return Response({'error': 'Category with this name already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        slug = _build_unique_category_slug(name)
        category = Category.objects.create(
            name=name,
            slug=slug,
            description=description,
            image=image,
            is_active=True,
        )
        
        return Response({
            'id': str(category.id),
            'name': category.name,
            'slug': category.slug,
            'description': category.description,
            'image': category.image.url if category.image else None,
            'created_at': category.created_at.isoformat(),
            'message': 'Category created successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def admin_update_category(request, category_id):
    """Update a category"""
    if not request.user.is_superuser:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        category = Category.objects.get(id=category_id)
        
        name = request.data.get('name', '').strip()
        description = request.data.get('description', '').strip()
        image = request.FILES.get('image')
        
        if not name:
            return Response({'error': 'Category name is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if category with this name already exists (excluding current category)
        if Category.objects.filter(name__iexact=name).exclude(id=category_id).exists():
            return Response({'error': 'Category with this name already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        category.name = name
        category.slug = _build_unique_category_slug(name, exclude_id=category.id)
        category.description = description
        
        # Update image if provided
        if image:
            category.image = image
            
        category.save()
        
        return Response({
            'id': str(category.id),
            'name': category.name,
            'slug': category.slug,
            'description': category.description,
            'image': category.image.url if category.image else None,
            'updated_at': category.updated_at.isoformat(),
            'message': 'Category updated successfully'
        })
        
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def admin_delete_category(request, category_id):
    """Delete a category"""
    if not request.user.is_superuser:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        category = Category.objects.get(id=category_id)
        category_name = category.name
        
        # Check if there are products associated with this category
        from products.models import Product
        product_count = Product.objects.filter(category=category).count()
        if product_count > 0:
            return Response({
                'error': f'Cannot delete category "{category_name}" because it has {product_count} product(s) associated with it. Please reassign or delete the products first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if there are subcategories
        subcategory_count = Category.objects.filter(parent=category).count()
        if subcategory_count > 0:
            return Response({
                'error': f'Cannot delete category "{category_name}" because it has {subcategory_count} subcategory(ies) associated with it. Please delete or reassign the subcategories first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        category.delete()
        
        return Response({
            'message': f'Category "{category_name}" deleted successfully'
        })
        
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': f'Error deleting category: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

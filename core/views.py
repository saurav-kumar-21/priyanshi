from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django.db.models import Q
from core.email_notifications import send_admin_alert_email
import json
from .models import ContactMessage, Newsletter, WebsiteRequest, ContactMessage, SiteSettings, Banner
from django.utils import timezone
import json
import logging


logger = logging.getLogger(__name__)

def home(request):
    """Home page view"""
    # Get site settings
    site_settings = SiteSettings.objects.first()
    
    # Get active banners - use the model method instead of property
    active_banners = []
    for banner in Banner.objects.filter(is_active=True).order_by('sort_order'):
        if banner.is_currently_active():
            active_banners.append(banner)
    
    # Get latest products and active categories
    from products.models import Product, Category
    latest_products = Product.objects.filter(
        status='active'
    ).select_related('category').prefetch_related('images').order_by('-created_at')[:8]
    categories = Category.objects.filter(is_active=True).order_by('name')[:12]
    
    context = {
        'site_settings': site_settings,
        'active_banners': active_banners,
        'latest_products': latest_products,
        'categories': categories,
    }
    
    return render(request, 'core/home.html', context)

def about(request):
    """About page view"""
    return render(request, 'core/about.html')

def is21store(request):
    """IS21 Store page view"""
    return render(request, 'core/is21store.html')

def register(request):
    """User registration page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/register.html', {'site_settings': site_settings})

def verify_email(request):
    """Email verification page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/verify_email.html', {'site_settings': site_settings})

def login(request):
    """User login page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/login.html', {'site_settings': site_settings})

def seller_register(request):
    """Seller registration page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/seller_register.html', {'site_settings': site_settings})

def reset_password(request):
    """Password reset request page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/reset_password.html', {'site_settings': site_settings})

def logout_view(request):
    """Logout page (client-side JWT cleanup + API POST)"""
    logout(request)
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/logout.html', {'site_settings': site_settings})

def contact(request):
    """Contact page view"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/contact.html', {'site_settings': site_settings})

def privacy(request):
    """Privacy policy page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/privacy.html', {'site_settings': site_settings})

def terms(request):
    """Terms of service page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/terms.html', {'site_settings': site_settings})

@require_POST
def newsletter_subscribe(request):
    """Handle newsletter subscription"""
    try:
        is_json = 'application/json' in (request.content_type or '')
        data = json.loads(request.body or '{}') if is_json else request.POST
        email = (data.get('email') or '').strip().lower()
        
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required'}, status=400)
        
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'success': False, 'message': 'Enter a valid email address'}, status=400)
        
        # Check if already subscribed
        if Newsletter.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': 'Email already subscribed'}, status=400)
        
        # Create new subscription
        Newsletter.objects.create(email=email)
        
        return JsonResponse({'success': True, 'message': 'Successfully subscribed!'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid request format'}, status=400)
    except Exception:
        logger.exception('Newsletter subscription failed')
        return JsonResponse({'success': False, 'message': 'Something went wrong'}, status=500)

@require_POST
def contact_submit(request):
    """Handle contact form submission"""
    try:
        is_json = 'application/json' in (request.content_type or '')
        data = json.loads(request.body or '{}') if is_json else request.POST
        
        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip().lower()
        subject = (data.get('subject') or '').strip()
        message = (data.get('message') or '').strip()
        
        if not all([name, email, subject, message]):
            return JsonResponse({'success': False, 'message': 'All fields are required'}, status=400)
        
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'success': False, 'message': 'Enter a valid email address'}, status=400)
        
        # Create contact message
        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        
        return JsonResponse({'success': True, 'message': 'Message sent successfully!'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid request format'}, status=400)
    except Exception:
        logger.exception('Contact form submission failed')
        return JsonResponse({'success': False, 'message': 'Something went wrong'}, status=500)

def products(request):
    """Products listing page"""
    site_settings = SiteSettings.objects.first()
    
    # Get filters
    search_query = (request.GET.get('search') or '').strip()
    selected_category = (request.GET.get('category') or '').strip()
    
    # Get products from database
    from products.models import Product, Category
    products_list = Product.objects.filter(status='active').select_related('category').order_by('-created_at')
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    # Apply category filter
    if selected_category:
        products_list = products_list.filter(category_id=selected_category)

    # Apply search filter
    if search_query:
        products_list = products_list.filter(
            Q(name__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    context = {
        'site_settings': site_settings,
        'search_query': search_query,
        'selected_category': selected_category,
        'categories': categories,
        'products': products_list,
    }
    
    return render(request, 'core/products_list.html', context)

def product_detail(request, product_id):
    """Product detail page"""
    site_settings = SiteSettings.objects.first()
    
    # Get product from database
    from products.models import Product
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images'),
        id=product_id,
        status='active'
    )
    
    context = {
        'site_settings': site_settings,
        'product': product,
        'admin_upi_id': getattr(settings, 'ADMIN_UPI_ID', ''),
    }
    
    return render(request, 'core/product_detail.html', context)

def checkout_details(request, product_id):
    """Checkout step 1: collect delivery details."""
    site_settings = SiteSettings.objects.first()
    from products.models import Product
    product = get_object_or_404(Product, id=product_id, status='active')

    requested_quantity = request.GET.get('quantity', 1)
    try:
        initial_quantity = int(requested_quantity)
    except (TypeError, ValueError):
        initial_quantity = 1
    initial_quantity = max(initial_quantity, 1)

    if product.track_inventory and product.quantity > 0:
        initial_quantity = min(initial_quantity, product.quantity)

    context = {
        'site_settings': site_settings,
        'product': product,
        'initial_quantity': initial_quantity,
    }
    return render(request, 'core/checkout_details.html', context)

def checkout_payment(request, product_id):
    """Checkout step 2: payment instruction and screenshot submission."""
    site_settings = SiteSettings.objects.first()
    from products.models import Product
    product = get_object_or_404(Product, id=product_id, status='active')

    context = {
        'site_settings': site_settings,
        'product': product,
        'admin_upi_id': getattr(settings, 'ADMIN_UPI_ID', ''),
    }
    return render(request, 'core/checkout_payment.html', context)

def sellers(request):
    """Sellers listing page"""
    site_settings = SiteSettings.objects.first()
    
    # Get featured sellers (this would be implemented with actual seller data)
    from sellers.models import Seller
    featured_sellers = Seller.objects.filter(
        approval_status='approved',
        is_featured=True
    ).order_by('-created_at')
    
    context = {
        'site_settings': site_settings,
        'featured_sellers': featured_sellers,
    }
    
    return render(request, 'core/sellers.html', context)

def seller_detail(request, seller_id):
    """Seller detail page"""
    site_settings = SiteSettings.objects.first()
    
    try:
        from sellers.models import Seller
        seller = Seller.objects.get(id=seller_id, approval_status='approved')
    except Seller.DoesNotExist:
        return render(request, 'core/404.html', {'site_settings': site_settings})
    
    context = {
        'site_settings': site_settings,
        'seller': seller,
    }
    
    return render(request, 'core/seller_detail.html', context)

def custom_404(request, exception):
    """Custom 404 page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/404.html', {'site_settings': site_settings}, status=404)

def test_template(request):
    """Test template rendering"""
    if not settings.DEBUG and not (request.user.is_authenticated and request.user.is_superuser):
        return HttpResponse(status=404)

    from django.template import Context, Template
    from django.utils import timezone
    
    template = Template('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
        </head>
        <body>
            <h1>Template System Working!</h1>
            <p>If you can see this page, the Django template system is working correctly.</p>
            <p>Time: {{ current_time }}</p>
        </body>
        </html>
    ''')
    
    context = Context({
        'current_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    return HttpResponse(template.render(context))

def custom_500(request):
    """Custom 500 page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/500.html', {'site_settings': site_settings}, status=500)

@login_required
def user_profile(request):
    """User profile page"""
    site_settings = SiteSettings.objects.first()
    from accounts.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(
        request,
        'core/user_profile.html',
        {
            'site_settings': site_settings,
            'profile': profile,
        }
    )

@login_required
def user_addresses(request):
    """User addresses page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/user_addresses.html', {'site_settings': site_settings})

@login_required
def user_cart(request):
    """User cart page"""
    site_settings = SiteSettings.objects.first()
    from cart.models import Cart

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('product').prefetch_related('product__images')

    context = {
        'site_settings': site_settings,
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'core/cart.html', context)

@login_required
def user_orders(request):
    """User orders view - regular users can see their own orders"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    site_settings = SiteSettings.objects.first()
    
    # Get user's orders only
    from orders.models import Order
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    payment_status_filter = request.GET.get('payment_status')
    if payment_status_filter:
        orders = orders.filter(payment_status=payment_status_filter)
    
    context = {
        'site_settings': site_settings,
        'orders': orders,
    }
    return render(request, 'core/user_orders_list.html', context)

def admin_orders(request):
    """Admin orders management"""
    if not request.user.is_superuser:
        return redirect('home')  # or show permission denied
    
    site_settings = SiteSettings.objects.first()
    
    # Get all orders for admin
    from orders.models import Order
    orders = Order.objects.select_related('user').order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    payment_status_filter = request.GET.get('payment_status')
    if payment_status_filter:
        orders = orders.filter(payment_status=payment_status_filter)

    pending_orders = Order.objects.filter(status='pending').count()
    confirmed_orders = Order.objects.filter(status='confirmed').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    
    context = {
        'site_settings': site_settings,
        'orders': orders,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
    }
    return render(request, 'core/admin_orders.html', context)

@login_required
def seller_dashboard(request):
    """Seller dashboard page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/seller_dashboard.html', {'site_settings': site_settings})

@login_required
def seller_products(request):
    """Manage products page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/seller_products.html', {'site_settings': site_settings})

@login_required
def seller_orders(request):
    """Seller orders page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/seller_orders.html', {'site_settings': site_settings})

@login_required
def seller_analytics(request):
    """Sales analytics page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/seller_analytics.html', {'site_settings': site_settings})

@login_required
def seller_profile(request):
    """Seller profile page"""
    site_settings = SiteSettings.objects.first()
    return render(request, 'core/seller_profile.html', {'site_settings': site_settings})

@require_http_methods(["POST"])
def website_request_api(request):
    """API endpoint for website requests"""
    try:
        # Parse JSON data
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['name', 'email', 'mobile', 'website_type', 'budget']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }, status=400)
        
        # Create website request
        website_request = WebsiteRequest.objects.create(
            name=data['name'],
            email=data['email'],
            mobile=data['mobile'],
            website_type=data['website_type'],
            budget=data['budget'],
            details=data.get('details', '')
        )
        
        send_admin_alert_email(
            f'New Website Request: {data["name"]}',
            'admin_website_request',
            {'website_request': website_request},
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Website request submitted successfully',
            'request_id': str(website_request.id)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
        
    except Exception as e:
        logger.error(f"Website request API error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

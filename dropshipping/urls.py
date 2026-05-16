"""
URL configuration for dropshipping project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.decorators.cache import never_cache
from core import views as core_views
import core.admin_views as admin_views
from core import admin_api_views

urlpatterns = [
    path(
        'service-worker.js',
        never_cache(TemplateView.as_view(
            template_name='service-worker.js',
            content_type='application/javascript'
        )),
        name='service_worker'
    ),
    path('sauravkumar141020099241/', admin.site.urls),
    
    # API URLs
    path('api/auth/', include('accounts.urls')),
    path('api/products/', include('products.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/sellers/', include('sellers.urls')),
    path('api/cart/', include('cart.urls')),
    
    # Admin API URLs
    path('api/admin/users/<uuid:user_id>/', admin_api_views.admin_user_detail, name='admin_user_detail'),
    path('api/admin/users/<uuid:user_id>/toggle/', admin_api_views.admin_toggle_user_status, name='admin_toggle_user_status'),
    path('api/admin/users/<uuid:user_id>/delete/', admin_api_views.admin_delete_user, name='admin_delete_user'),
    path('api/admin/sellers/<uuid:seller_id>/', admin_api_views.admin_seller_detail, name='admin_seller_detail'),
    path('api/admin/sellers/<uuid:seller_id>/edit/', admin_api_views.admin_edit_seller, name='admin_edit_seller'),
    path('api/admin/sellers/<uuid:seller_id>/approve/', admin_api_views.admin_approve_seller, name='admin_approve_seller'),
    path('api/admin/sellers/<uuid:seller_id>/reject/', admin_api_views.admin_reject_seller, name='admin_reject_seller'),
    path('api/admin/sellers/<uuid:seller_id>/suspend/', admin_api_views.admin_suspend_seller, name='admin_suspend_seller'),
    path('api/admin/sellers/<uuid:seller_id>/reactivate/', admin_api_views.admin_reactivate_seller, name='admin_reactivate_seller'),
    path('api/admin/sellers/<uuid:seller_id>/delete/', admin_api_views.admin_delete_seller, name='admin_delete_seller'),
    path('api/admin/orders/<int:order_id>/', admin_api_views.admin_order_detail, name='admin_order_detail'),
    path('api/admin/orders/<int:order_id>/update-status/', admin_api_views.admin_update_order_status, name='admin_update_order_status'),
    path('api/admin/orders/delete-cancelled/', admin_api_views.admin_delete_cancelled_orders, name='admin_delete_cancelled_orders'),
    
    # Category Management API URLs
    path('api/admin/categories/', admin_api_views.admin_category_list, name='admin_category_list'),
    path('api/admin/categories/create/', admin_api_views.admin_create_category, name='admin_create_category'),
    path('api/admin/categories/<uuid:category_id>/', admin_api_views.admin_update_category, name='admin_update_category'),
    path('api/admin/categories/<uuid:category_id>/delete/', admin_api_views.admin_delete_category, name='admin_delete_category'),
    
    # Frontend URLs
    path('', core_views.home, name='home'),
    path('home/', core_views.home, name='home'),
    path('test/', core_views.test_template, name='test'),
    path('register/', core_views.register, name='register'),
    path('login/', core_views.login, name='login'),
    path('logout/', core_views.logout_view, name='logout'),
    path('reset-password/', core_views.reset_password, name='reset_password'),
    path('verify-email/', core_views.verify_email, name='verify_email'),
    path('about/', core_views.about, name='about'),
    path('is21store/', core_views.is21store, name='is21store'),
    path('contact/', core_views.contact, name='contact'),
    path('privacy/', core_views.privacy, name='privacy'),
    path('terms/', core_views.terms, name='terms'),
    path('products/', core_views.products, name='products'),
    path('products/<uuid:product_id>/', core_views.product_detail, name='product_detail'),
    path('checkout/<uuid:product_id>/details/', core_views.checkout_details, name='checkout_details'),
    path('checkout/<uuid:product_id>/payment/', core_views.checkout_payment, name='checkout_payment'),
    path('sellers/', core_views.sellers, name='sellers'),
    path('sellers/<uuid:seller_id>/', core_views.seller_detail, name='seller_detail'),
    path('profile/', core_views.user_profile, name='user_profile'),
    path('addresses/', core_views.user_addresses, name='user_addresses'),
    path('cart/', core_views.user_cart, name='user_cart'),
    path('orders/', core_views.user_orders, name='user_orders'),
    path('admin-panel/login/', admin_views.AdminLoginView.as_view(), name='admin_login'),
    path('admin-panel/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', admin_views.admin_users, name='admin_users'),
    path('admin-panel/sellers/', admin_views.admin_sellers, name='admin_sellers'),
    path('admin-panel/products/', admin_views.admin_products, name='admin_products'),
    path('admin-panel/orders/', core_views.admin_orders, name='admin_orders'),
    path('admin-panel/categories/', admin_views.admin_categories, name='admin_categories'),
    path('admin-panel/activities/', admin_views.admin_activities, name='admin_activities'),
    path('admin-panel/contacts/', admin_views.admin_contact_messages, name='admin_contact_messages'),
    path('admin-panel/messages/', admin_views.admin_messages, name='admin_messages'),
    path('admin-panel/website-requests/', admin_views.admin_website_requests, name='admin_website_requests'),
    # Frontend API endpoints
    path('api/newsletter/subscribe/', core_views.newsletter_subscribe, name='api_newsletter_subscribe'),
    path('newsletter/subscribe/', core_views.newsletter_subscribe, name='newsletter_subscribe'),
    path('contact/submit/', core_views.contact_submit, name='contact_submit'),
    path('api/website-request/', core_views.website_request_api, name='website_request_api'),
]

# Custom error handlers
handler404 = core_views.custom_404
handler500 = core_views.custom_500

# Serve media and static files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT)

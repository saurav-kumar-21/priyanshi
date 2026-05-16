from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
import os
import cloudinary
import cloudinary.uploader
from core.models import SiteSettings, Banner
from products.models import Category, ProductImage
from orders.models import Order
from sellers.models import Seller


class Command(BaseCommand):
    help = 'Migrate existing images from local storage to Cloudinary'

    def handle(self, *args, **options):
        self.stdout.write('Starting migration to Cloudinary...')
        
        # Check if Cloudinary credentials are configured
        cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', '')
        api_key = getattr(settings, 'CLOUDINARY_API_KEY', '')
        api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', '')
        
        if not all([cloud_name, api_key, api_secret]):
            self.stdout.write(self.style.ERROR('Cloudinary credentials are not configured. Please check your .env file.'))
            return
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
        )

        # Migrate SiteSettings images
        self.migrate_site_settings()
        
        # Migrate Banner images
        self.migrate_banners()
        
        # Migrate Category images
        self.migrate_categories()
        
        # Migrate Product images
        self.migrate_product_images()
        
        # Migrate Order screenshots
        self.migrate_order_screenshots()
        
        # Migrate Seller logos
        self.migrate_seller_logos()
        
        self.stdout.write(self.style.SUCCESS('Migration to Cloudinary completed successfully!'))

    def migrate_site_settings(self):
        """Migrate SiteSettings images"""
        self.stdout.write('Migrating SiteSettings images...')
        site_settings = SiteSettings.objects.first()
        if site_settings:
            if site_settings.site_logo:
                self.upload_to_cloudinary(site_settings, 'site_logo', 'site_settings/site_logo')
            if site_settings.favicon:
                self.upload_to_cloudinary(site_settings, 'favicon', 'site_settings/favicon')

    def migrate_banners(self):
        """Migrate Banner images"""
        self.stdout.write('Migrating Banner images...')
        banners = Banner.objects.all()
        for banner in banners:
            if banner.image:
                self.upload_to_cloudinary(banner, 'image', f'banners/banner_{banner.id}')

    def migrate_categories(self):
        """Migrate Category images"""
        self.stdout.write('Migrating Category images...')
        categories = Category.objects.all()
        for category in categories:
            if category.image:
                self.upload_to_cloudinary(category, 'image', f'categories/category_{category.id}')

    def migrate_product_images(self):
        """Migrate Product images"""
        self.stdout.write('Migrating Product images...')
        product_images = ProductImage.objects.all()
        for img in product_images:
            if img.image:
                self.upload_to_cloudinary(img, 'image', f'products/product_{img.product.id}_img_{img.id}')

    def migrate_order_screenshots(self):
        """Migrate Order screenshots"""
        self.stdout.write('Migrating Order screenshots...')
        orders = Order.objects.all()
        for order in orders:
            if order.payment_screenshot:
                self.upload_to_cloudinary(order, 'payment_screenshot', f'orders/payments/order_{order.id}_payment')
            if order.refund_screenshot:
                self.upload_to_cloudinary(order, 'refund_screenshot', f'orders/refunds/order_{order.id}_refund')

    def migrate_seller_logos(self):
        """Migrate Seller logos"""
        self.stdout.write('Migrating Seller logos...')
        sellers = Seller.objects.all()
        for seller in sellers:
            if seller.logo:
                self.upload_to_cloudinary(seller, 'logo', f'sellers/logos/seller_{seller.id}_logo')

    def upload_to_cloudinary(self, instance, field_name, public_id):
        """Upload image to Cloudinary and update the field"""
        try:
            image_field = getattr(instance, field_name)
            if not image_field:
                return

            # Read the image file
            image_path = image_field.path
            if not os.path.exists(image_path):
                self.stdout.write(self.style.WARNING(f'Image file not found: {image_path}'))
                return

            # Upload to Cloudinary
            with open(image_path, 'rb') as f:
                upload_result = cloudinary.uploader.upload(
                    f,
                    public_id=public_id,
                    folder='skyraa_store',
                    resource_type='image',
                    overwrite=True
                )

            # Update the field with Cloudinary URL
            cloudinary_url = upload_result['secure_url']
            setattr(instance, field_name, cloudinary_url)
            instance.save()

            self.stdout.write(self.style.SUCCESS(f'✓ Uploaded {field_name} for {instance.__class__.__name__} {instance.id}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Failed to upload {field_name} for {instance.__class__.__name__}: {str(e)}'))

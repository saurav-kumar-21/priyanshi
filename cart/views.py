from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from products.models import Product
import logging


logger = logging.getLogger(__name__)

class CartView(generics.RetrieveAPIView):
    """Get user's cart"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart
    
    def retrieve(self, request, *args, **kwargs):
        cart = self.get_object()
        serializer = CartSerializer(cart)
        return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_to_cart(request):
    """Add product to cart"""
    try:
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        product = get_object_or_404(Product, id=product_id, status='active')
        
        if product.quantity < quantity:
            return Response({
                'error': 'Not enough stock available',
                'available': product.quantity
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                'quantity': quantity,
                'price': product.price
            }
        )
        
        if not created:
            # Update existing item
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = CartSerializer(cart)
        return Response({
            'success': True,
            'message': 'Product added to cart',
            'cart': serializer.data
        })
    
    except Exception:
        logger.exception('Failed to add item to cart')
        return Response({
            'success': False,
            'error': 'Unable to add this item to cart right now.'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    try:
        quantity = int(request.data.get('quantity', 1))
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        
        if quantity <= 0:
            cart_item.delete()
            return Response({
                'success': True,
                'message': 'Item removed from cart'
            })
        
        cart_item.quantity = quantity
        cart_item.save()
        
        # Get updated cart
        cart = cart_item.cart
        serializer = CartSerializer(cart)
        return Response({
            'success': True,
            'message': 'Cart updated',
            'cart': serializer.data
        })
        
    except Exception:
        logger.exception('Failed to update cart item')
        return Response({
            'success': False,
            'error': 'Unable to update cart right now.'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()
        
        # Get updated cart
        cart = Cart.objects.get(user=request.user)
        serializer = CartSerializer(cart)
        return Response({
            'success': True,
            'message': 'Item removed from cart',
            'cart': serializer.data
        })
        
    except Exception:
        logger.exception('Failed to remove cart item')
        return Response({
            'success': False,
            'error': 'Unable to remove item right now.'
        }, status=status.HTTP_400_BAD_REQUEST)

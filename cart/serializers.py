from rest_framework import serializers
from .models import Cart, CartItem
from products.serializers import ProductListSerializer

class CartItemSerializer(serializers.ModelSerializer):
    """Cart item serializer"""
    product = ProductListSerializer(read_only=True)
    subtotal = serializers.ReadOnlyField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'price', 'subtotal']

class CartSerializer(serializers.ModelSerializer):
    """Cart serializer"""
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_items', 'total_price', 'created_at']

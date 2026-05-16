from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.CartView.as_view(), name='cart'),
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('item/<uuid:item_id>/update/', views.update_cart_item, name='update_cart_item'),
    path('item/<uuid:item_id>/remove/', views.remove_from_cart, name='remove_from_cart'),
]

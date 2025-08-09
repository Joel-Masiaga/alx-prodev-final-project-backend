from .models import Product, Cart, CartItem, Transaction
from .serializers import (
    ProductSerializer, 
    DetailedProductSerializer, 
    CartSerializer, 
    CartItemSerializer,
    SimpleCartSerializer
)
from users.serializers import UserSerializer
from users.models import User
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from decimal import Decimal
from django.conf import settings
import uuid
import requests
from django.conf import settings

BASE_URL = settings.REACT_BASE_URL

@api_view(['GET'])
@permission_classes([AllowAny])
def products(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    serializer = DetailedProductSerializer(product)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def add_item(request):
    try:
        cart_code = request.data.get('cart_code')
        product_id = request.data.get('product_id')

        cart, created = Cart.objects.get_or_create(cart_code=cart_code)
        product = Product.objects.get(id=product_id)

        cartitem, created = CartItem.objects.get_or_create(cart=cart, product=product)
        cartitem.quantity = 1
        cartitem.save()

        serializer = CartItemSerializer(cartitem)
        return Response({'data': serializer.data, 'message': "Cart item added successfully"}, status=201)
    
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    

@api_view(['GET'])
@permission_classes([AllowAny])
def product_in_cart(request):
    cart_code = request.query_params.get('cart_code')
    product_id = request.query_params.get('product_id')
    cart = Cart.objects.get(cart_code=cart_code)
    product = Product.objects.get(id=product_id)

    product_exists_in_cart = CartItem.objects.filter(cart=cart, product=product).exists()
    return Response({'product_in_cart': product_exists_in_cart})

@api_view(['GET'])
@permission_classes([AllowAny])
def get_cart_stat(request):
    cart_code = request.query_params.get('cart_code')
    cart = Cart.objects.get(cart_code=cart_code, paid=False)
    serializer = SimpleCartSerializer(cart)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_cart(request):
    cart_code = request.query_params.get('cart_code')
    cart = Cart.objects.get(cart_code=cart_code, paid=False)
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['PATCH'])
@permission_classes([AllowAny])
def update_quantity(request):
    try:
        cartitem_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        quantity = int(quantity)
        cartitem = CartItem.objects.get(id=cartitem_id)
        cartitem.quantity = quantity
        cartitem.save()
        serializer = CartItemSerializer(cartitem)
        return Response({'data': serializer.data, 'message': "Cart item updated successfully!"}, status=201)
    
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_cartitem(request):
    cartitem_id = request.data.get('item_id')
    cartitem = CartItem.objects.get(id=cartitem_id)
    cartitem.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


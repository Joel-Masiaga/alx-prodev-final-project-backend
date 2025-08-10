from uuid import uuid4
import uuid
from decimal import Decimal
import requests

from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Product, Cart, CartItem, Transaction
from .serializers import (
    ProductSerializer,
    DetailedProductSerializer,
    CartSerializer,
    CartItemSerializer,
    SimpleCartSerializer
)
from users.models import User


BASE_URL = settings.REACT_BASE_URL


def get_or_create_cart(request):
    """
    Retrieve or create a Cart object:
    - For authenticated users: get/create by user and paid=False
    - For guests: get/create by cart_code and paid=False; generate cart_code if missing
    """
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user, paid=False)
    else:
        cart_code = request.query_params.get('cart_code') or request.data.get('cart_code')
        if not cart_code:
            cart_code = str(uuid4())
        cart, created = Cart.objects.get_or_create(cart_code=cart_code, paid=False)
    return cart


@extend_schema(
    summary="List all products",
    responses=ProductSerializer(many=True)
)
@api_view(['GET'])
@permission_classes([AllowAny])
def products(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@extend_schema(
    summary="Retrieve detailed product information",
    parameters=[
        OpenApiParameter(name="slug", description="Product slug", required=True, type=OpenApiTypes.STR)
    ],
    responses=DetailedProductSerializer
)
@api_view(['GET'])
@permission_classes([AllowAny])
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    serializer = DetailedProductSerializer(product)
    return Response(serializer.data)


@extend_schema(
    summary="Add item to cart",
    request=CartItemSerializer,
    responses={
        201: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT
    },
    examples=[
        OpenApiExample(
            "Add to cart example",
            value={"cart_code": "abc123", "product_id": 1, "quantity": 2}
        )
    ]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def add_item(request):
    try:
        cart = get_or_create_cart(request)

        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'product_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        quantity = int(request.data.get('quantity', 1))
        if quantity < 1:
            return Response({'error': 'Quantity must be at least 1.'}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, id=product_id)

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        serializer = CartItemSerializer(cart_item)
        response_data = serializer.data

        if not request.user.is_authenticated:
            response_data['cart_code'] = cart.cart_code

        return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def product_in_cart(request):
    cart = get_or_create_cart(request)

    product_id = request.query_params.get('product_id')
    if not product_id:
        return Response({'error': 'product_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    product = get_object_or_404(Product, id=product_id)
    exists = CartItem.objects.filter(cart=cart, product=product).exists()
    return Response({'product_in_cart': exists})


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def get_cart(request):
    cart_code = request.query_params.get('cart_code')

    if request.user.is_authenticated:
        # Logged-in user: retrieve or create their single cart
        cart = Cart.objects.filter(user=request.user, paid=False).first()
        if not cart:
            cart = Cart.objects.create(
                user=request.user,
                cart_code=uuid.uuid4().hex
            )
    else:
        # Guest: retrieve or create by cart_code
        if cart_code:
            cart = Cart.objects.filter(cart_code=cart_code, paid=False).first()
        else:
            cart = None

        if not cart:
            cart = Cart.objects.create(cart_code=uuid.uuid4().hex)

    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_cart_stat(request):
    cart_code = request.query_params.get('cart_code')
    cart = Cart.objects.get(cart_code=cart_code, paid=False)
    serializer = SimpleCartSerializer(cart)
    return Response(serializer.data)

@api_view(['PATCH'])
@permission_classes([AllowAny])
def update_quantity(request):
    try:
        cart = get_or_create_cart(request)

        cartitem_id = request.data.get('item_id')
        quantity = request.data.get('quantity')

        if not cartitem_id or quantity is None:
            return Response({'error': 'item_id and quantity are required.'}, status=status.HTTP_400_BAD_REQUEST)

        quantity = int(quantity)
        if quantity < 1:
            return Response({'error': 'Quantity must be at least 1.'}, status=status.HTTP_400_BAD_REQUEST)

        cart_item = get_object_or_404(CartItem, id=cartitem_id, cart=cart)
        cart_item.quantity = quantity
        cart_item.save()

        serializer = CartItemSerializer(cart_item)
        return Response({'data': serializer.data, 'message': "Cart item updated successfully!"}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_cartitem(request, item_id):
    cart = get_or_create_cart(request)

    try:
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except CartItem.DoesNotExist:
        return Response({"error": "Cart item not found."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    try:
        user = request.user
        cart = get_or_create_cart(request)

        if cart.paid:
            return Response({'error': 'Cart already paid.'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate total amount
        amount = sum(item.quantity * item.product.price for item in cart.items.all())
        tax = Decimal('4.00')
        total_amount = amount + tax
        currency = "USD"
        redirect_url = f'{BASE_URL}/payment-status/'

        # Generate transaction reference
        tx_ref = str(uuid4())

        transaction = Transaction.objects.create(
            ref=tx_ref,
            cart=cart,
            amount=total_amount,
            currency=currency,
            user=user,
            status='pending'
        )

        flutterwave_payload = {
            'tx_ref': tx_ref,
            'amount': str(total_amount),
            'currency': currency,
            'redirect_url': redirect_url,
            'customer': {
                'email': user.email,
                'phonenumber': getattr(user.profile, 'phone', '') if hasattr(user, 'profile') else ''
            },
            'customizations': {
                'title': "Duka+ Payment"
            }
        }

        headers = {
            'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
            'Content-Type': 'application/json'
        }

        response = requests.post(
            'https://api.flutterwave.com/v3/payments',
            json=flutterwave_payload,
            headers=headers
        )

        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        else:
            return Response(response.json(), status=response.status_code)

    except requests.exceptions.RequestException as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payment_callback(request):
    status_param = request.GET.get('status')
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')
    user = request.user

    if status_param == 'successful':
        headers = {
            'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}'
        }
        response = requests.get(f'https://api.flutterwave.com/v3/transactions/{transaction_id}/verify', headers=headers)
        response_data = response.json()

        if response_data.get('status') == 'success':
            try:
                transaction = Transaction.objects.get(ref=tx_ref)
            except Transaction.DoesNotExist:
                return Response({'message': 'Transaction not found.'}, status=status.HTTP_404_NOT_FOUND)

            data = response_data.get('data', {})
            if (data.get('status') == 'successful' and
                float(data.get('amount', 0)) == float(transaction.amount) and
                data.get('currency') == transaction.currency):

                transaction.status = 'completed'
                transaction.save()

                cart = transaction.cart
                cart.paid = True
                cart.user = user
                cart.save()

                return Response({'message': 'Payment successful!', 'subMessage': 'You have successfully paid!'})

            else:
                return Response({'message': 'Payment verification failed', 'subMessage': 'Your payment verification failed!'}, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({'message': 'Failed to verify transaction with Flutterwave', 'subMessage': 'We could not verify your transaction!'}, status=status.HTTP_400_BAD_REQUEST)

    else:
        return Response({'message': 'Payment was not successful'}, status=status.HTTP_400_BAD_REQUEST)

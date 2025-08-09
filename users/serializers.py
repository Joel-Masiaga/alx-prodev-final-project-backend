from .models import User, Profile
from store.serializers import NewCartItemSerializer, CartSerializer
from store.models import CartItem
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['id', 'password', 'password2', 'email', 'role']
    
    def validate(sefl, attr):
        if attr['password'] != attr['password2']:
            raise serializers.ValidationError({"password": "Password Fields didn't match!"})
        return attr
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'password', 'email', 'role', 'items']
        extra_kwargs = {"password": {"write_only": True}}
        
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
    
    def get_items(self, user):
        cartitems = CartItem.objects.filter(cart__user=user, cart__paid=True)[:10]
        serializer = NewCartItemSerializer(cartitems, many=True)
        return serializer.data
    
class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'user', 'first_name', 'last_name', 'country', 'city', 'address', 'phone', 'bio', 'image']
        read_only_fields = ['user']


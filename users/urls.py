from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    CreateUserView, 
    BlacklistTokenView,
    get_useremail,
    user_info,
)

urlpatterns = [
    path('register/', CreateUserView.as_view(), name='register'),
    path('logout/blacklist/', BlacklistTokenView.as_view(), name='blacklist'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('get_useremail', get_useremail, name='get_useremail'),
    path('user_info', user_info, name='user_info'),
]
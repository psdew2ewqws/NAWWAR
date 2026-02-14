"""
User API views.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.users import services, selectors
from apps.users.api.serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
)


class UserListApi(APIView):
    """List all users."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = selectors.user_list()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class UserCreateApi(APIView):
    """Create a new user (registration)."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = services.user_create(**serializer.validated_data)

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )


class UserMeApi(APIView):
    """Current user profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = services.user_update(
            user=request.user,
            data=serializer.validated_data
        )

        return Response(UserSerializer(user).data)

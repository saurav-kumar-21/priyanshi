from rest_framework import serializers
from accounts.models import User

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 
            'phone', 'date_of_birth', 'role', 'is_active', 
            'is_email_verified', 'is_phone_verified', 'created_at', 'last_login'
        ]
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or "Not Set"

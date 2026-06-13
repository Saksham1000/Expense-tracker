from rest_framework import serializers

from .models import Category, Expense


class CategorySerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = Category
        fields = ["id", "name", "description", "monthly_limit", "owner"]


class ExpenseSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = Expense
        fields = ["id", "title", "amount", "currency", "category", "date", "notes", "owner"]

    def validate_category(self, value):
        request = self.context.get("request")
        if request and value.owner != request.user:
            raise serializers.ValidationError("Category does not belong to the authenticated user.")
        return value

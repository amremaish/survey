from rest_framework import serializers


class PaginationQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, default=1, min_value=1, help_text="Page number (1-based)")
    page_size = serializers.IntegerField(required=False, default=10, min_value=1, max_value=100, help_text="Number of items per page")



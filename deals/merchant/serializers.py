from rest_framework import serializers
from deals.serializers import DealSerializer


class DashboardStatsSerializer(serializers.Serializer):
    total_deals = serializers.IntegerField()
    active_deals = serializers.IntegerField()
    completed_deals = serializers.IntegerField()
    disputed_deals = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    recent_deals = DealSerializer(many=True)


class PaymentLinkSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.SlugField()
    link_url = serializers.CharField()
    item_description = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    delivery_days = serializers.IntegerField()

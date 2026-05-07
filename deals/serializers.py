from rest_framework import serializers
from .models import Deal, Transaction, Dispute


class DealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deal
        fields = '__all__'
        read_only_fields = ['id', 'slug', 'status', 'va_account_number',
                            'va_bank_name', 'va_reference', 'created_at',
                            'paid_at', 'shipped_at', 'auto_release_at',
                            'completed_at']


class DealCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deal
        fields = ['item_description', 'amount', 'delivery_days',
                  'buyer_email', 'buyer_phone']


class DealPayResponseSerializer(serializers.Serializer):
    va_account_number = serializers.CharField()
    va_bank_name = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'


class DisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispute
        fields = ['id', 'deal', 'reason', 'status', 'created_at', 'resolved_at']
        read_only_fields = ['id', 'status', 'created_at', 'resolved_at']


class DisputeCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)


class AdminDisputeSerializer(serializers.ModelSerializer):
    deal = DealSerializer(read_only=True)

    class Meta:
        model = Dispute
        fields = '__all__'

from rest_framework import serializers
from .models import Property

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = '__all__'
        read_only_fields = (
            'owner',
            'zsa_asset_id',
            'zcash_operation_id',
            'zcash_txid',
            'tokenization_status',
            'tokenization_error',
            'tokenized_at',
            'status',
            'created_at',
        )

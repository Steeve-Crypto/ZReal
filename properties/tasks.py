"""
Celery tasks for ZReal.

These tasks handle background processing for:
- ZSA transaction confirmation polling
"""

from celery import shared_task
import logging

from properties.models import Property
from zcash_integration.zcash_client import ZcashClient

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def poll_zsa_confirmation(self, property_id, txid):
    """
    Poll Zcash node to confirm ZSA issuance transaction.
    Updates property status once confirmed.
    """
    try:
        prop = Property.objects.get(id=property_id)
        operation = prop.tokenization_operations.filter(operation_id=txid).first()
        if not operation:
            operation = prop.tokenization_operations.filter(txid=txid).first()
        if not operation or not operation.operation_id:
            logger.warning("No refreshable tokenization operation found for property=%s id=%s", property_id, txid)
            return

        result = ZcashClient().refresh_zsa_status(operation.operation_id)
        operation.mark_from_result(result)
        prop.tokenization_status = operation.status
        prop.zcash_txid = operation.txid or prop.zcash_txid
        prop.zsa_asset_id = operation.asset_id or prop.zsa_asset_id
        prop.tokenization_error = operation.error

        if operation.status == 'confirmed':
            prop.status = 'tokenized'
            prop.tokenized_at = operation.confirmed_at
            prop.save()
            logger.info("Property %s ZSA confirmed", property_id)
        elif operation.status == 'failed':
            prop.save()
            logger.error("Property %s ZSA failed: %s", property_id, operation.error)
        else:
            prop.save()
            raise self.retry(countdown=30)

    except Property.DoesNotExist:
        logger.error(f"Property {property_id} not found")
    except Exception as exc:
        logger.error(f"Error polling ZSA confirmation: {exc}")
        raise self.retry(exc=exc, countdown=60)

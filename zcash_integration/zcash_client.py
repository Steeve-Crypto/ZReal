"""
Zcash RPC Client for ZReal
Handles transparent + shielded transactions.
Ready for Zcash Shielded Assets (ZSA) when full RPC support lands.
"""

import requests
import json
import os
from django.conf import settings

class ZcashClient:
    def __init__(self):
        self.rpc_url = settings.ZCASH_RPC_URL
        self.session = requests.Session()

    def _call(self, method, params=None):
        payload = {
            "jsonrpc": "1.0",
            "id": "zreal",
            "method": method,
            "params": params or []
        }
        try:
            response = self.session.post(self.rpc_url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_blockchain_info(self):
        return self._call("getblockchaininfo")

    def get_balance(self, address=None):
        """Get balance. For shielded, use z_getbalance or viewing keys."""
        if address:
            return self._call("z_getbalance", [address])
        return self._call("getbalance")

    def z_sendmany(self, fromaddress, amounts, minconf=1, fee=0.0001, privacyPolicy="AllowFullyShielded"):
        """
        Send shielded or mixed transaction.
        amounts: list of {"address": "...", "amount": 0.1, "memo": "optional json"}
        """
        params = [fromaddress, amounts, minconf, fee, privacyPolicy]
        return self._call("z_sendmany", params)

    def issue_zsa_placeholder(self, property_id, total_shares, issuer_zaddr, memo_data=None):
        """
        Placeholder for Zcash Shielded Asset issuance.
        In production (post full ZSA activation): Use dedicated ZSA mint RPC or zcash_tx_tool.
        Currently uses z_sendmany with rich memo containing asset metadata.
        """
        memo = json.dumps({
            "type": "zsa_issuance",
            "property_id": property_id,
            "total_shares": total_shares,
            "asset_name": f"ZReal-Property-{property_id}",
            **(memo_data or {})
        })
        
        # Example: Send 0 value tx with memo to self or designated address
        amounts = [{
            "address": issuer_zaddr,
            "amount": 0.0001,  # Small fee amount
            "memo": memo
        }]
        
        return self.z_sendmany(issuer_zaddr, amounts, privacyPolicy="AllowFullyShielded")

    def get_zsa_balance_placeholder(self, zaddr):
        """Future: Proper ZSA balance query via viewing key or new RPC."""
        return self._call("z_getbalance", [zaddr])

    # ==================== FULL ZSA ISSUANCE + SHIELDED DISTRIBUTION ====================

    def create_zsa_issuance_tx(self, issuer_zaddr: str, property_id: int, total_shares: int, 
                               asset_symbol: str = None, memo_extra: dict = None, 
                               use_tx_tool: bool = True):
        """
        Creates a shielded transaction that represents ZSA issuance.
        
        Enhanced in 2026 with optional zcash_tx_tool support for more robust ZSA flows.
        
        use_tx_tool=True (default): Attempts to use QED-it/zcash_tx_tool for advanced issuance.
        Falls back to rich-memo RPC method if tool unavailable or fails.
        """
        if use_tx_tool:
            return self.create_zsa_issuance_with_tx_tool(issuer_zaddr, property_id, total_shares, asset_symbol)
        
        # Original rich-memo fallback
        asset_symbol = asset_symbol or f"ZREAL-PROP-{property_id}"
        
        memo_data = {
            "action": "zsa_issuance",
            "property_id": property_id,
            "total_shares": total_shares,
            "asset_symbol": asset_symbol,
            "issued_by": issuer_zaddr,
            "timestamp": timezone.now().isoformat(),
            **(memo_extra or {})
        }
        
        memo = json.dumps(memo_data)
        
        amounts = [{
            "address": issuer_zaddr,
            "amount": 0.00001,
            "memo": memo
        }]
        
        tx_result = self.z_sendmany(
            fromaddress=issuer_zaddr,
            amounts=amounts,
            privacyPolicy="AllowFullyShielded"
        )
        
        return {
            "tx_result": tx_result,
            "memo_data": memo_data,
            "note": "ZSA record created via rich memo (fallback). Consider installing zcash_tx_tool for advanced flows."
        }

    def distribute_shielded_payments(self, from_zaddr: str, recipients: list, 
                                     memo_base: dict = None):
        """
        Shielded distribution flow (e.g. rental income, dividends to ZSA holders).
        
        recipients: list of dicts -> [{"zaddr": "...", "amount": 0.05, "investor_id": 123}, ...]
        
        Returns list of tx results. All transfers are fully shielded.
        """
        results = []
        
        for recipient in recipients:
            memo_data = {
                "action": "zsa_distribution",
                "property_id": memo_base.get("property_id") if memo_base else None,
                "investor_id": recipient.get("investor_id"),
                "shares": recipient.get("shares"),
                **(memo_base or {})
            }
            
            amounts = [{
                "address": recipient["zaddr"],
                "amount": recipient["amount"],
                "memo": json.dumps(memo_data)
            }]
            
            tx = self.z_sendmany(
                fromaddress=from_zaddr,
                amounts=amounts,
                privacyPolicy="AllowFullyShielded"
            )
            
            results.append({
                "recipient_zaddr": recipient["zaddr"],
                "amount": recipient["amount"],
                "tx_result": tx
            })
        
        return results

    def get_shielded_tx_details(self, txid: str):
        """Fetch details of a shielded transaction (for confirmation)."""
        return self._call("getrawtransaction", [txid, 1])

    # ==================== ZSA ISSUANCE STRATEGY (Adaptable for Native ZSA) ====================
    #
    # ZReal uses a strategy-based approach for ZSA issuance to remain adaptable.
    #
    # Current strategies:
    #   1. zcash_tx_tool (preferred when available)
    #   2. Rich memo via z_sendmany (reliable fallback)
    #
    # Future strategy (when native ZSA is fully activated on mainnet):
    #   3. Direct native OrchardZSA issuance via new RPC methods
    #
    # This structure minimizes future refactoring.

    def _get_tx_tool_path(self):
        """Returns path to zcash_tx_tool binary if available."""
        import shutil
        tool_path = os.environ.get('ZCASH_TX_TOOL_PATH', shutil.which('zcash_tx_tool'))
        if tool_path and os.path.exists(tool_path):
            return tool_path
        return None

    def create_zsa_issuance_with_tx_tool(self, issuer_zaddr: str, property_id: int, total_shares: int, 
                                         asset_symbol: str = None):
        """
        Enhanced ZSA issuance using zcash_tx_tool (recommended for production ZSA).
        
        Falls back to rich-memo RPC method if tool is not available.
        
        Requires zcash_tx_tool to be built and in PATH or ZCASH_TX_TOOL_PATH env var.
        See: https://github.com/QED-it/zcash_tx_tool
        """
        import subprocess
        import os
        
        tool_path = self._get_tx_tool_path()
        
        if not tool_path:
            # Fallback to existing rich memo method
            return self.create_zsa_issuance_tx(issuer_zaddr, property_id, total_shares, asset_symbol)
        
        asset_symbol = asset_symbol or f"ZREAL-PROP-{property_id}"
        
        # Build command for zcash_tx_tool (example - adjust based on actual CLI)
        # This is a conceptual integration. Real usage depends on the tool's exact interface.
        cmd = [
            tool_path,
            "create-zsa-issuance",
            "--from", issuer_zaddr,
            "--property-id", str(property_id),
            "--total-shares", str(total_shares),
            "--asset-symbol", asset_symbol,
            "--network", "testnet"  # or mainnet
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                txid = result.stdout.strip()
                return {
                    "success": True,
                    "txid": txid,
                    "method": "zcash_tx_tool",
                    "asset_symbol": asset_symbol,
                    "note": "ZSA issuance created via zcash_tx_tool"
                }
            else:
                # Fallback on error
                return self.create_zsa_issuance_tx(issuer_zaddr, property_id, total_shares, asset_symbol)
        except Exception as e:
            # Fallback
            return self.create_zsa_issuance_tx(issuer_zaddr, property_id, total_shares, asset_symbol)

    # ==================== SAPLING-SPECIFIC RPC INTEGRATION ====================

    def generate_sapling_address(self, address_type: str = "sapling"):
        """
        Generate a new Sapling shielded address.
        address_type: 'sapling' (recommended) or 'transparent'
        """
        if address_type == "sapling":
            return self._call("z_getnewaddress", ["sapling"])
        else:
            return self._call("getnewaddress")

    def get_sapling_balance(self, zaddr: str = None, minconf: int = 1):
        """
        Get balance for a specific Sapling address or all shielded funds.
        """
        if zaddr:
            return self._call("z_getbalance", [zaddr, minconf])
        # Get total shielded balance
        return self._call("z_gettotalbalance", [minconf])

    def list_sapling_unspent(self, zaddr: str = None, minconf: int = 1):
        """
        List unspent Sapling notes (very useful for building transactions manually
        or showing available shielded funds).
        """
        params = [minconf]
        if zaddr:
            params.insert(0, [zaddr])
        return self._call("z_listunspent", params)

    def export_viewing_key(self, zaddr: str):
        """
        Export the viewing key for a Sapling address.
        This is powerful for the SaaS: allow investors to share read-only access
        to their shielded portfolio without revealing spending keys.
        """
        return self._call("z_exportviewingkey", [zaddr])

    def import_viewing_key(self, viewing_key: str, rescan: str = "whenkeyisnew"):
        """
        Import a viewing key (for read-only access to shielded funds).
        """
        return self._call("z_importviewingkey", [viewing_key, rescan])

    def get_sapling_address_type(self, zaddr: str):
        """
        Check if an address is Sapling, Orchard, or transparent.
        """
        # z_validateaddress works for both transparent and shielded
        result = self._call("z_validateaddress", [zaddr])
        return result.get("result", {})

    def create_sapling_shielded_tx(self, from_zaddr: str, to_zaddr: str, amount: float,
                                   memo: str = None, privacy_policy: str = "AllowFullyShielded"):
        """
        Convenience method for simple Sapling-to-Sapling transfers.
        """
        amounts = [{
            "address": to_zaddr,
            "amount": amount,
            "memo": memo
        }]
        return self.z_sendmany(
            fromaddress=from_zaddr,
            amounts=amounts,
            privacyPolicy=privacy_policy
        )

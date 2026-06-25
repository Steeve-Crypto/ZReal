"""
Zcash/ZSA integration boundary for ZReal.

ZReal does not fake ZSA issuance. The issuance path requires a configured
external ZSA-capable tool and stores only the IDs returned by that tool.
"""

import json
import os
import re
import shlex
import shutil
import string
import subprocess

import requests
from django.conf import settings


class ZcashConfigurationError(RuntimeError):
    pass


class ZcashToolOutputError(RuntimeError):
    pass


class ZcashClient:
    ALLOWED_BACKENDS = {"zcash_tx_tool"}
    ALLOWED_STATUSES = {"pending", "broadcast", "confirmed", "failed"}
    ISSUE_REQUIRED_FIELDS = {"tool", "issuer_zaddr", "asset_symbol", "total_shares"}
    STATUS_REQUIRED_FIELDS = {"tool", "operation_id"}
    TEMPLATE_FIELDS = {
        "tool",
        "issuer_zaddr",
        "asset_symbol",
        "total_shares",
        "network",
        "metadata_json",
        "metadata_file",
        "operation_id",
    }

    def __init__(self):
        self.rpc_url = settings.ZCASH_RPC_URL
        self.network = settings.ZCASH_NETWORK
        self.session = requests.Session()

    def _call(self, method, params=None):
        if not self.rpc_url:
            raise ZcashConfigurationError(
                "ZCASH_RPC_URL is not configured. Set ZCASH_RPC_URL or ZCASHRPC_USER/"
                "ZCASHRPC_PASSWORD/ZCASHRPC_HOST in .env."
            )

        payload = {
            "jsonrpc": "1.0",
            "id": "zreal",
            "method": method,
            "params": params or [],
        }
        response = self.session.post(self.rpc_url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        return data.get("result")

    def get_blockchain_info(self):
        return self._call("getblockchaininfo")

    def _validate_shielded_address_shape(self, address):
        if not address:
            raise ValueError("Issuer shielded address is required.")
        if any(ch.isspace() for ch in address):
            raise ValueError("Issuer shielded address must not contain whitespace.")
        if not re.fullmatch(r"[A-Za-z0-9]+", address):
            raise ValueError("Issuer shielded address contains unsupported characters.")
        if not address.startswith(("z", "u")):
            raise ValueError("Issuer address must be a shielded Sapling or Unified address.")
        if len(address) < 20:
            raise ValueError("Issuer shielded address is too short.")

    def validate_address(self, address):
        self._validate_shielded_address_shape(address)
        if not self.rpc_url:
            return {
                "isvalid": True,
                "warning": "Address was shape-checked only because ZCASH_RPC_URL is not configured.",
            }
        result = self._call("z_validateaddress", [address])
        if not result.get("isvalid"):
            raise ValueError(f"Invalid issuer shielded address: {result}")
        return result

    def _tx_tool_path(self):
        configured = settings.ZCASH_TX_TOOL_PATH
        if configured:
            return configured
        return shutil.which("zcash_tx_tool")

    def _template_fields(self, template):
        return {
            field_name
            for _, field_name, _, _ in string.Formatter().parse(template or "")
            if field_name
        }

    def _validate_template_for_report(self, template, required_fields, purpose):
        missing = []
        warnings = []
        if not template:
            missing.append(f"{purpose} command template")
            return missing, warnings

        fields = self._template_fields(template)
        unknown = fields - self.TEMPLATE_FIELDS
        missing_fields = required_fields - fields
        if unknown:
            warnings.append(
                f"{purpose} command template contains unsupported placeholder(s): {', '.join(sorted(unknown))}."
            )
        if missing_fields:
            missing.append(
                f"{purpose} command placeholder(s): {', '.join(sorted(missing_fields))}"
            )
        return missing, warnings

    def configuration_report(self):
        """Return a safe, non-secret ZSA configuration report without issuing tokens."""
        backend = settings.ZSA_ISSUANCE_BACKEND
        tool = self._tx_tool_path()
        missing = []
        warnings = []

        if backend not in self.ALLOWED_BACKENDS:
            missing.append("supported ZSA_ISSUANCE_BACKEND")
            warnings.append(
                f"Unsupported ZSA_ISSUANCE_BACKEND '{backend}'. Supported: {', '.join(sorted(self.ALLOWED_BACKENDS))}."
            )

        if not self.network:
            missing.append("ZCASH_NETWORK")

        if not self.rpc_url:
            missing.append("ZCASH_RPC_URL")

        tool_exists = False
        if not tool:
            missing.append("ZCASH_TX_TOOL_PATH or zcash_tx_tool on PATH")
        else:
            tool_exists = os.path.exists(tool)
            if not tool_exists:
                missing.append("existing ZCASH_TX_TOOL_PATH")

        issue_missing, issue_warnings = self._validate_template_for_report(
            settings.ZCASH_ZSA_ISSUE_COMMAND,
            self.ISSUE_REQUIRED_FIELDS,
            "ZSA issue",
        )
        status_missing, status_warnings = self._validate_template_for_report(
            settings.ZCASH_ZSA_STATUS_COMMAND,
            self.STATUS_REQUIRED_FIELDS,
            "ZSA status",
        )
        missing.extend(issue_missing)
        missing.extend(status_missing)
        warnings.extend(issue_warnings)
        warnings.extend(status_warnings)

        command_preparable = False
        if settings.ZCASH_ZSA_ISSUE_COMMAND and tool:
            context = {
                "tool": tool,
                "issuer_zaddr": "ztestsapling1validationaddress",
                "asset_symbol": "ZREAL-VALIDATION",
                "total_shares": 1,
                "network": self.network or "missing-network",
                "metadata_json": "{}",
                "metadata_file": "",
                "operation_id": "validation-operation-id",
            }
            try:
                shlex.split(settings.ZCASH_ZSA_ISSUE_COMMAND.format(**context), posix=os.name != "nt")
                command_preparable = True
            except Exception as exc:
                missing.append("safely preparable ZSA issue command")
                warnings.append(f"ZSA issue command could not be prepared safely: {exc}")

        missing = sorted(set(missing))
        warnings = sorted(set(warnings))

        return {
            "configured": bool(backend or tool or settings.ZCASH_ZSA_ISSUE_COMMAND or settings.ZCASH_ZSA_STATUS_COMMAND),
            "ready": not missing and command_preparable,
            "missing": missing,
            "warnings": warnings,
            "method": backend,
            "backend": backend,
            "network": self.network or "",
            "tool_path_configured": bool(settings.ZCASH_TX_TOOL_PATH),
            "tool_path_exists": tool_exists,
            "tool_path_display": tool or "",
            "issue_command_configured": bool(settings.ZCASH_ZSA_ISSUE_COMMAND),
            "status_command_configured": bool(settings.ZCASH_ZSA_STATUS_COMMAND),
            "rpc_url_configured": bool(self.rpc_url),
            "command_preparable": command_preparable,
            "safe_display": {
                "backend": backend,
                "network": self.network or "",
                "tool_path": tool or "",
                "issue_placeholders": sorted(self._template_fields(settings.ZCASH_ZSA_ISSUE_COMMAND)),
                "status_placeholders": sorted(self._template_fields(settings.ZCASH_ZSA_STATUS_COMMAND)),
            },
        }

    def validate_command_template(self, template, required_fields, purpose):
        if not template:
            raise ZcashConfigurationError(f"{purpose} command template is not configured.")

        fields = {
            field_name
            for _, field_name, _, _ in string.Formatter().parse(template)
            if field_name
        }
        unknown = fields - self.TEMPLATE_FIELDS
        missing = required_fields - fields
        if unknown:
            raise ZcashConfigurationError(
                f"{purpose} command template contains unsupported placeholder(s): {', '.join(sorted(unknown))}."
            )
        if missing:
            raise ZcashConfigurationError(
                f"{purpose} command template is missing required placeholder(s): {', '.join(sorted(missing))}."
            )
        return fields

    def validate_issue_configuration(self, issuer_zaddr, asset_symbol, total_shares, metadata=None):
        backend = settings.ZSA_ISSUANCE_BACKEND
        if backend not in self.ALLOWED_BACKENDS:
            raise ZcashConfigurationError(
                f"Unsupported ZSA_ISSUANCE_BACKEND '{backend}'. Supported: {', '.join(sorted(self.ALLOWED_BACKENDS))}."
            )
        tool = self._tx_tool_path()
        if not tool:
            raise ZcashConfigurationError(
                "ZCASH_TX_TOOL_PATH is not configured and zcash_tx_tool was not found on PATH."
            )
        if not os.path.exists(tool):
            raise ZcashConfigurationError(f"Configured ZCASH_TX_TOOL_PATH does not exist: {tool}")
        if not self.rpc_url:
            raise ZcashConfigurationError("ZCASH_RPC_URL is not configured.")
        self.validate_address(issuer_zaddr)
        if not asset_symbol or not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,63}", asset_symbol):
            raise ValueError("Asset symbol must be 3-64 characters using uppercase letters, numbers, '_' or '-'.")
        if int(total_shares) <= 0:
            raise ValueError("Total shares must be greater than zero.")
        self.validate_command_template(settings.ZCASH_ZSA_ISSUE_COMMAND, self.ISSUE_REQUIRED_FIELDS, "ZSA issue")
        if metadata is not None:
            json.dumps(metadata, sort_keys=True)

    def validate_status_configuration(self):
        tool = self._tx_tool_path()
        if not tool:
            raise ZcashConfigurationError(
                "ZCASH_TX_TOOL_PATH is not configured and zcash_tx_tool was not found on PATH."
            )
        if not os.path.exists(tool):
            raise ZcashConfigurationError(f"Configured ZCASH_TX_TOOL_PATH does not exist: {tool}")
        if not self.rpc_url:
            raise ZcashConfigurationError("ZCASH_RPC_URL is not configured.")
        self.validate_command_template(settings.ZCASH_ZSA_STATUS_COMMAND, self.STATUS_REQUIRED_FIELDS, "ZSA status")

    def _parse_tool_output(self, stdout):
        stdout = stdout.strip()
        if not stdout:
            raise ZcashToolOutputError("ZSA tool returned no output.")
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ZcashToolOutputError("ZSA tool must return a JSON object.") from exc
        if not isinstance(data, dict):
            raise ZcashToolOutputError("ZSA tool output must be a JSON object.")

        status = data.get("status")
        if status is not None and status not in self.ALLOWED_STATUSES:
            raise ZcashToolOutputError(f"Unsupported ZSA status returned by tool: {status}")

        if not any(data.get(key) for key in ("operation_id", "txid", "asset_id")):
            raise ZcashToolOutputError("ZSA tool output did not include operation_id, txid, or asset_id.")

        if status == "confirmed" and not data.get("asset_id"):
            raise ZcashToolOutputError("Confirmed ZSA output must include asset_id.")

        if status is None:
            if data.get("asset_id"):
                data["status"] = "confirmed"
            elif data.get("txid"):
                data["status"] = "broadcast"
            else:
                data["status"] = "pending"
        return data

    def _run_tool_command(self, template, context, metadata=None):
        metadata_json = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"))
        context = {
            **context,
            "tool": self._tx_tool_path(),
            "network": self.network,
            "metadata_json": metadata_json,
            "metadata_file": "",
        }
        command = template.format(**context)
        result = subprocess.run(
            shlex.split(command, posix=os.name != "nt"),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env={**os.environ, "ZREAL_ZSA_METADATA_JSON": metadata_json},
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ZSA tool failed.")

        return self._parse_tool_output(result.stdout)

    def issue_zsa(self, issuer_zaddr, asset_symbol, total_shares, metadata=None):
        self.validate_issue_configuration(issuer_zaddr, asset_symbol, total_shares, metadata=metadata)
        data = self._run_tool_command(
            settings.ZCASH_ZSA_ISSUE_COMMAND,
            {
                "issuer_zaddr": issuer_zaddr,
                "asset_symbol": asset_symbol,
                "total_shares": total_shares,
            },
            metadata=metadata,
        )
        data["backend"] = settings.ZSA_ISSUANCE_BACKEND
        return data

    def refresh_zsa_status(self, operation_id):
        if not operation_id:
            raise ValueError("operation_id is required to refresh pending ZSA status.")
        self.validate_status_configuration()
        data = self._run_tool_command(
            settings.ZCASH_ZSA_STATUS_COMMAND,
            {"operation_id": operation_id},
        )
        data["backend"] = settings.ZSA_ISSUANCE_BACKEND
        return data

    def generate_sapling_address(self, address_type="sapling"):
        if address_type == "sapling":
            return self._call("z_getnewaddress", ["sapling"])
        return self._call("getnewaddress")

"""
Django admin configuration for the blockchain app.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import TransactionLog, ContractEvent, TxLogStatus


class ContractEventInline(admin.TabularInline):
    model = ContractEvent
    extra = 0
    readonly_fields = ("event_type", "log_index", "block_number", "emitter_wallet", "event_data_preview")
    fields          = ("event_type", "log_index", "block_number", "emitter_wallet", "event_data_preview")
    can_delete      = False
    max_num         = 0

    @admin.display(description="Event Data")
    def event_data_preview(self, obj):
        import json
        data = json.dumps(obj.event_data, indent=2)
        return format_html("<pre style='font-size:11px;max-width:300px;overflow:auto'>{}</pre>", data)


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = (
        "id", "tx_type", "from_wallet_short", "value_matic",
        "status_badge", "confirmations", "block_number", "created_at",
    )
    list_filter  = ("status", "tx_type", "chain_id", "created_at")
    search_fields = ("tx_hash", "from_wallet", "to_wallet")
    ordering      = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "id", "tx_hash", "tx_type", "from_wallet", "to_wallet",
        "chain_id", "block_number", "block_hash", "block_timestamp",
        "value_wei", "value_matic", "gas_used", "gas_limit",
        "gas_price_gwei", "status", "confirmations",
        "jar_id_ref", "donation_id_ref", "raw_receipt",
        "created_at", "confirmed_at", "explorer_link",
    )
    inlines = [ContractEventInline]

    @admin.display(description="From")
    def from_wallet_short(self, obj):
        addr = obj.from_wallet
        return format_html('<code>{}</code>', f"{addr[:6]}…{addr[-4:]}")

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            TxLogStatus.PENDING:   "#f59e0b",
            TxLogStatus.CONFIRMED: "#10b981",
            TxLogStatus.FAILED:    "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.display(description="PolygonScan")
    def explorer_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">{}</a>',
            obj.explorer_url, obj.tx_hash,
        )


@admin.register(ContractEvent)
class ContractEventAdmin(admin.ModelAdmin):
    list_display = (
        "id", "event_type", "chain_jar_id", "emitter_wallet_short",
        "block_number", "tx_hash_short", "created_at",
    )
    list_filter  = ("event_type", "created_at")
    search_fields = ("tx_hash", "emitter_wallet", "chain_jar_id")
    ordering      = ("-block_number", "log_index")
    readonly_fields = (
        "id", "tx_log", "tx_hash", "event_type", "log_index",
        "block_number", "block_timestamp", "event_data",
        "chain_jar_id", "emitter_wallet", "created_at",
    )

    @admin.display(description="Emitter")
    def emitter_wallet_short(self, obj):
        addr = obj.emitter_wallet
        if not addr:
            return "—"
        return format_html('<code>{}</code>', f"{addr[:6]}…{addr[-4:]}")

    @admin.display(description="Tx Hash")
    def tx_hash_short(self, obj):
        return format_html('<code>{}</code>', f"{obj.tx_hash[:12]}…")

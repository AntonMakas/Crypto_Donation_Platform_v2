"""
Django admin configuration for the donations app.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Donation, TxStatus


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    # ── List view ──────────────────────────────────────────────────
    list_display = (
        "id", "jar_link", "donor_wallet_short", "amount_matic",
        "tx_status_badge", "is_verified", "confirmations",
        "verification_attempts", "created_at",
    )
    list_filter  = (
        "tx_status", "is_verified", "is_anonymous", "created_at",
    )
    search_fields = (
        "donor_wallet", "tx_hash", "jar__title", "message",
    )
    ordering       = ("-created_at",)
    date_hierarchy = "created_at"

    readonly_fields = (
        "id", "jar", "donor", "donor_wallet", "amount_matic", "amount_wei",
        "tx_hash", "tx_hash_link", "block_number", "block_timestamp",
        "gas_used", "gas_price_gwei", "confirmations",
        "is_verified", "verified_at", "last_verified_at",
        "verification_attempts", "created_at", "updated_at",
    )

    fieldsets = (
        ("Donation", {
            "fields": ("jar", "donor", "donor_wallet", "amount_matic", "amount_wei",
                       "message", "is_anonymous"),
        }),
        ("Transaction", {
            "fields": ("tx_hash", "tx_hash_link", "tx_status", "block_number",
                       "block_timestamp", "gas_used", "gas_price_gwei"),
        }),
        ("Verification", {
            "fields": ("is_verified", "verified_at", "confirmations",
                       "verification_attempts", "last_verified_at"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["trigger_verification", "mark_confirmed_manually"]

    @admin.action(description="Trigger blockchain verification for selected donations")
    def trigger_verification(self, request, queryset):
        from apps.blockchain.tasks import verify_single_transaction
        count = 0
        for donation in queryset.filter(tx_status=TxStatus.PENDING):
            verify_single_transaction.delay(donation.tx_hash)
            count += 1
        self.message_user(request, f"Queued verification for {count} donation(s).")

    @admin.action(description="⚠️  Manually mark as confirmed (use with caution)")
    def mark_confirmed_manually(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(tx_status=TxStatus.PENDING).update(
            tx_status=TxStatus.CONFIRMED,
            is_verified=True,
            verified_at=timezone.now(),
        )
        self.message_user(request, f"Manually confirmed {updated} donation(s).")

    # ── Custom display ─────────────────────────────────────────────
    @admin.display(description="Jar", ordering="jar__title")
    def jar_link(self, obj):
        from django.urls import reverse
        url = reverse("admin:jars_jar_change", args=[obj.jar_id])
        return format_html('<a href="{}">#{} {}</a>', url, obj.jar_id, obj.jar.title[:30])

    @admin.display(description="Donor", ordering="donor_wallet")
    def donor_wallet_short(self, obj):
        addr = obj.donor_wallet
        return format_html('<code>{}</code>', f"{addr[:6]}…{addr[-4:]}")

    @admin.display(description="Status")
    def tx_status_badge(self, obj):
        colors = {
            TxStatus.PENDING:   "#f59e0b",
            TxStatus.CONFIRMED: "#10b981",
            TxStatus.FAILED:    "#ef4444",
            TxStatus.REPLACED:  "#6b7280",
        }
        color = colors.get(obj.tx_status, "#6b7280")
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            color, obj.get_tx_status_display(),
        )

    @admin.display(description="Tx Hash")
    def tx_hash_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">{}</a>',
            obj.explorer_url,
            obj.tx_hash,
        )

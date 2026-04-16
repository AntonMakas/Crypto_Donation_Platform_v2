"""
Django admin configuration for the jars app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum

from .models import Jar, JarStatus


class DonationInline(admin.TabularInline):
    """Show donations inline within the Jar admin detail page."""
    from apps.donations.models import Donation
    model = Donation
    extra = 0
    readonly_fields = (
        "donor_wallet", "amount_matic", "tx_status",
        "is_verified", "tx_hash_link", "created_at",
    )
    fields = (
        "donor_wallet", "amount_matic", "tx_status",
        "is_verified", "tx_hash_link", "created_at",
    )
    can_delete = False
    max_num = 0   # Read-only inline

    @admin.display(description="Tx Hash")
    def tx_hash_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">{}</a>',
            obj.explorer_url,
            f"{obj.tx_hash[:12]}…",
        )


@admin.register(Jar)
class JarAdmin(admin.ModelAdmin):
    # ── List view ──────────────────────────────────────────────────
    list_display = (
        "id", "title", "creator_wallet_short", "status_badge",
        "progress_display", "deadline", "is_verified_on_chain",
        "donor_count", "created_at",
    )
    list_filter  = ("status", "category", "is_verified_on_chain", "created_at")
    search_fields = ("title", "creator_wallet", "creation_tx_hash", "chain_jar_id")
    ordering      = ("-created_at",)
    date_hierarchy = "created_at"

    readonly_fields = (
        "id", "chain_jar_id", "creator_wallet", "amount_raised_matic",
        "donor_count", "progress_display", "creation_tx_hash",
        "withdrawal_tx_hash", "withdrawn_at",
        "is_verified_on_chain", "created_at", "updated_at",
        "explorer_link",
    )

    fieldsets = (
        ("Campaign", {
            "fields": ("title", "description", "category", "cover_emoji", "cover_image_url"),
        }),
        ("Creator", {
            "fields": ("creator", "creator_wallet"),
        }),
        ("Fundraising", {
            "fields": ("target_amount_matic", "amount_raised_matic", "deadline",
                       "progress_display", "donor_count"),
        }),
        ("Status", {
            "fields": ("status",),
        }),
        ("Blockchain", {
            "fields": ("chain_jar_id", "creation_tx_hash", "is_verified_on_chain", "explorer_link"),
        }),
        ("Withdrawal", {
            "fields": ("withdrawal_tx_hash", "withdrawn_at"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    inlines = [DonationInline]

    # ── Admin actions ──────────────────────────────────────────────
    actions = ["mark_verified", "sync_statuses"]

    @admin.action(description="Mark selected jars as verified on-chain")
    def mark_verified(self, request, queryset):
        updated = queryset.update(is_verified_on_chain=True)
        self.message_user(request, f"{updated} jar(s) marked as verified.")

    @admin.action(description="Sync statuses for selected jars")
    def sync_statuses(self, request, queryset):
        synced = 0
        for jar in queryset:
            if jar.sync_status():
                synced += 1
        self.message_user(request, f"Synced {synced} jar(s). {queryset.count() - synced} unchanged.")

    # ── Custom display columns ─────────────────────────────────────
    @admin.display(description="Creator", ordering="creator_wallet")
    def creator_wallet_short(self, obj):
        addr = obj.creator_wallet
        return format_html('<code>{}</code>', f"{addr[:6]}…{addr[-4:]}")

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            JarStatus.ACTIVE:    "#10b981",
            JarStatus.COMPLETED: "#7c3aed",
            JarStatus.EXPIRED:   "#f59e0b",
            JarStatus.WITHDRAWN: "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.display(description="Progress")
    def progress_display(self, obj):
        pct = obj.progress_percentage
        bar_color = "#10b981" if pct >= 100 else "#7c3aed" if pct >= 70 else "#f59e0b"
        return format_html(
            '<div style="width:120px;background:#1f2937;border-radius:4px;height:8px;">'
            '<div style="width:{:.0f}%;background:{};height:8px;border-radius:4px;"></div>'
            '</div>'
            '<span style="font-size:11px;color:#9ca3af">{:.1f}%</span>',
            min(pct, 100), bar_color, pct,
        )

    @admin.display(description="PolygonScan")
    def explorer_link(self, obj):
        url = obj.explorer_url
        if not url:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">View ↗</a>', url)

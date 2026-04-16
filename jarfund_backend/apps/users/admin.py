"""
Django admin configuration for the users app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # ── List view ──────────────────────────────────────────────────
    list_display   = (
        "wallet_address_short", "username", "is_verified",
        "is_staff", "created_at", "total_donated_display",
    )
    list_filter    = ("is_verified", "is_staff", "is_superuser", "created_at")
    search_fields  = ("wallet_address", "username")
    ordering       = ("-created_at",)
    readonly_fields = (
        "wallet_address", "nonce", "created_at", "updated_at",
        "last_login", "total_donated_display", "total_raised_display",
    )

    # ── Form layout ────────────────────────────────────────────────
    fieldsets = (
        ("Identity", {
            "fields": ("wallet_address", "username", "bio", "avatar_url"),
        }),
        ("Authentication", {
            "fields": ("nonce", "is_verified", "password"),
            "description": "Wallet auth uses nonce-based signature verification.",
        }),
        ("Stats", {
            "fields": ("total_donated_display", "total_raised_display"),
        }),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "last_login"),
            "classes": ("collapse",),
        }),
    )
    add_fieldsets = (
        ("Create User", {
            "fields": ("wallet_address", "password1", "password2"),
        }),
    )

    # ── Custom display columns ─────────────────────────────────────
    @admin.display(description="Wallet")
    def wallet_address_short(self, obj):
        addr = obj.wallet_address
        return format_html(
            '<code title="{}">{}</code>',
            addr,
            f"{addr[:6]}…{addr[-4:]}",
        )

    @admin.display(description="Total Donated")
    def total_donated_display(self, obj):
        return f"{obj.total_donated:.4f} MATIC"

    @admin.display(description="Total Raised")
    def total_raised_display(self, obj):
        return f"{obj.total_raised:.4f} MATIC"

"""
Users app initial migration.
Creates the custom User model.
Generated: 2026-03-01
"""
import secrets
import django.contrib.auth.models
import django.contrib.auth.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id",         models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("password",   models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, verbose_name="superuser status")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name",  models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email",      models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                ("is_staff",   models.BooleanField(default=False, verbose_name="staff status")),
                ("is_active",  models.BooleanField(default=True, verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("username",        models.CharField(blank=True, default="", max_length=80)),
                ("wallet_address",  models.CharField(db_index=True, max_length=42, unique=True)),
                ("nonce",           models.CharField(default=secrets.token_hex, max_length=64)),
                ("is_verified",     models.BooleanField(default=False)),
                ("bio",             models.TextField(blank=True, default="")),
                ("avatar_url",      models.URLField(blank=True, default="")),
                ("created_at",      models.DateTimeField(auto_now_add=True)),
                ("updated_at",      models.DateTimeField(auto_now=True)),
                ("last_login_at",   models.DateTimeField(blank=True, null=True)),
                ("groups",         models.ManyToManyField(blank=True, related_name="user_set",
                                    related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, related_name="user_set",
                                    related_query_name="user", to="auth.permission",
                                    verbose_name="user permissions")),
            ],
            options={
                "verbose_name":        "User",
                "verbose_name_plural": "Users",
                "ordering":            ["-created_at"],
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
    ]

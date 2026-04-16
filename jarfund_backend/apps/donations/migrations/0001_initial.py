"""
Donations app initial migration.
Creates the Donation model with all indexes and constraints.
Generated: 2026-03-01
"""
import decimal
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import apps.jars.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("jars", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Donation",
            fields=[
                ("id",                    models.BigAutoField(primary_key=True, serialize=False)),
                ("jar",                   models.ForeignKey(
                                              db_index=True,
                                              on_delete=django.db.models.deletion.PROTECT,
                                              related_name="donations",
                                              to="jars.jar",
                                          )),
                ("donor",                 models.ForeignKey(
                                              blank=True, null=True,
                                              on_delete=django.db.models.deletion.SET_NULL,
                                              related_name="donations_made",
                                              to=settings.AUTH_USER_MODEL,
                                          )),
                ("donor_wallet",          models.CharField(
                                              db_index=True, max_length=42,
                                              validators=[apps.jars.validators.validate_wallet_address],
                                          )),
                ("amount_matic",          models.DecimalField(
                                              decimal_places=6, max_digits=20,
                                              validators=[
                                                  django.core.validators.MinValueValidator(decimal.Decimal("0.001")),
                                                  apps.jars.validators.validate_min_donation,
                                              ],
                                          )),
                ("amount_wei",            models.CharField(default="0", max_length=78)),
                ("tx_hash",               models.CharField(
                                              db_index=True, max_length=66, unique=True,
                                              validators=[apps.jars.validators.validate_tx_hash],
                                          )),
                ("tx_status",             models.CharField(
                                              choices=[
                                                  ("pending","Pending"),("confirmed","Confirmed"),
                                                  ("failed","Failed"),("replaced","Replaced"),
                                              ],
                                              db_index=True, default="pending", max_length=10,
                                          )),
                ("block_number",          models.PositiveBigIntegerField(blank=True, null=True)),
                ("block_timestamp",       models.DateTimeField(blank=True, null=True)),
                ("gas_used",              models.PositiveBigIntegerField(blank=True, null=True)),
                ("gas_price_gwei",        models.DecimalField(blank=True, decimal_places=9, max_digits=20, null=True)),
                ("confirmations",         models.PositiveIntegerField(default=0)),
                ("is_verified",           models.BooleanField(db_index=True, default=False)),
                ("verified_at",           models.DateTimeField(blank=True, null=True)),
                ("verification_attempts", models.PositiveSmallIntegerField(default=0)),
                ("last_verified_at",      models.DateTimeField(blank=True, null=True)),
                ("message",               models.CharField(blank=True, default="", max_length=280)),
                ("is_anonymous",          models.BooleanField(default=False)),
                ("created_at",            models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at",            models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name":        "Donation",
                "verbose_name_plural": "Donations",
                "db_table":            "donations_donation",
                "ordering":            ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="donation",
            index=models.Index(fields=["tx_status", "is_verified"],          name="idx_donation_status_verified"),
        ),
        migrations.AddIndex(
            model_name="donation",
            index=models.Index(fields=["donor_wallet", "tx_status"],         name="idx_donation_donor_status"),
        ),
        migrations.AddIndex(
            model_name="donation",
            index=models.Index(fields=["jar", "tx_status"],                  name="idx_donation_jar_status"),
        ),
        migrations.AddIndex(
            model_name="donation",
            index=models.Index(fields=["tx_status", "verification_attempts"],name="idx_donation_pending_attempts"),
        ),
        migrations.AddConstraint(
            model_name="donation",
            constraint=models.CheckConstraint(
                check=models.Q(amount_matic__gte=decimal.Decimal("0.001")),
                name="chk_donation_min_amount",
            ),
        ),
    ]

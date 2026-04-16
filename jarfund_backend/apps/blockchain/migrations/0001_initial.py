"""
Blockchain app initial migration.
Creates TransactionLog and ContractEvent models.
Generated: 2026-03-01
"""
import django.db.models.deletion
from django.db import migrations, models
import apps.jars.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TransactionLog",
            fields=[
                ("id",             models.BigAutoField(primary_key=True, serialize=False)),
                ("tx_hash",        models.CharField(
                                       db_index=True, max_length=66, unique=True,
                                       validators=[apps.jars.validators.validate_tx_hash],
                                   )),
                ("tx_type",        models.CharField(
                                       choices=[
                                           ("create_jar","Create Jar"),("donate","Donate"),
                                           ("withdraw","Withdraw"),("other","Other"),
                                       ],
                                       db_index=True, max_length=12,
                                   )),
                ("from_wallet",    models.CharField(
                                       db_index=True, max_length=42,
                                       validators=[apps.jars.validators.validate_wallet_address],
                                   )),
                ("to_wallet",      models.CharField(blank=True, default="", max_length=42)),
                ("chain_id",       models.PositiveIntegerField(default=80002)),
                ("block_number",   models.PositiveBigIntegerField(blank=True, db_index=True, null=True)),
                ("block_hash",     models.CharField(blank=True, default="", max_length=66)),
                ("block_timestamp",models.DateTimeField(blank=True, null=True)),
                ("value_wei",      models.CharField(default="0", max_length=78)),
                ("value_matic",    models.DecimalField(decimal_places=6, default=0, max_digits=20)),
                ("gas_used",       models.PositiveBigIntegerField(blank=True, null=True)),
                ("gas_limit",      models.PositiveBigIntegerField(blank=True, null=True)),
                ("gas_price_wei",  models.CharField(blank=True, default="", max_length=30)),
                ("gas_price_gwei", models.DecimalField(blank=True, decimal_places=9, max_digits=20, null=True)),
                ("status",         models.CharField(
                                       choices=[
                                           ("pending","Pending"),("confirmed","Confirmed"),("failed","Failed"),
                                       ],
                                       db_index=True, default="pending", max_length=10,
                                   )),
                ("confirmations",  models.PositiveIntegerField(default=0)),
                ("jar_id_ref",     models.PositiveBigIntegerField(blank=True, null=True)),
                ("donation_id_ref",models.PositiveBigIntegerField(blank=True, null=True)),
                ("raw_receipt",    models.JSONField(blank=True, null=True)),
                ("created_at",     models.DateTimeField(auto_now_add=True, db_index=True)),
                ("confirmed_at",   models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name":        "Transaction Log",
                "verbose_name_plural": "Transaction Logs",
                "db_table":            "blockchain_transactionlog",
                "ordering":            ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ContractEvent",
            fields=[
                ("id",              models.BigAutoField(primary_key=True, serialize=False)),
                ("tx_log",          models.ForeignKey(
                                        blank=True, null=True,
                                        on_delete=django.db.models.deletion.CASCADE,
                                        related_name="events",
                                        to="blockchain.transactionlog",
                                    )),
                ("tx_hash",         models.CharField(
                                        db_index=True, max_length=66,
                                        validators=[apps.jars.validators.validate_tx_hash],
                                    )),
                ("event_type",      models.CharField(
                                        choices=[
                                            ("JarCreated","Jar Created"),
                                            ("DonationReceived","Donation Received"),
                                            ("FundsWithdrawn","Funds Withdrawn"),
                                            ("JarStatusChanged","Jar Status Changed"),
                                            ("PlatformFeeUpdated","Platform Fee Updated"),
                                        ],
                                        db_index=True, max_length=30,
                                    )),
                ("log_index",       models.PositiveIntegerField(default=0)),
                ("block_number",    models.PositiveBigIntegerField(db_index=True)),
                ("block_timestamp", models.DateTimeField(blank=True, null=True)),
                ("event_data",      models.JSONField(default=dict)),
                ("chain_jar_id",    models.PositiveBigIntegerField(blank=True, db_index=True, null=True)),
                ("emitter_wallet",  models.CharField(blank=True, db_index=True, default="", max_length=42)),
                ("created_at",      models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "verbose_name":        "Contract Event",
                "verbose_name_plural": "Contract Events",
                "db_table":            "blockchain_contractevent",
                "ordering":            ["-block_number", "log_index"],
            },
        ),
        migrations.AddIndex(
            model_name="transactionlog",
            index=models.Index(fields=["status", "tx_type"],      name="idx_txlog_status_type"),
        ),
        migrations.AddIndex(
            model_name="transactionlog",
            index=models.Index(fields=["from_wallet", "tx_type"], name="idx_txlog_wallet_type"),
        ),
        migrations.AddIndex(
            model_name="transactionlog",
            index=models.Index(fields=["block_number"],           name="idx_txlog_block"),
        ),
        migrations.AddIndex(
            model_name="contractevent",
            index=models.Index(fields=["event_type", "block_number"], name="idx_event_type_block"),
        ),
        migrations.AddIndex(
            model_name="contractevent",
            index=models.Index(fields=["chain_jar_id", "event_type"], name="idx_event_jar_type"),
        ),
        migrations.AddIndex(
            model_name="contractevent",
            index=models.Index(fields=["emitter_wallet"],             name="idx_event_wallet"),
        ),
        migrations.AlterUniqueTogether(
            name="contractevent",
            unique_together={("tx_hash", "log_index")},
        ),
    ]

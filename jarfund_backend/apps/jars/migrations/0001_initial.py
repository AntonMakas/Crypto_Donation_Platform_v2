"""
Jars app initial migration.
Creates the Jar model with all indexes and constraints.
Generated: 2026-03-01
"""
import decimal
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
import apps.jars.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Jar",
            fields=[
                ("id",                   models.BigAutoField(primary_key=True, serialize=False)),
                ("chain_jar_id",         models.PositiveBigIntegerField(blank=True, db_index=True, null=True, unique=True)),
                ("creator",              models.ForeignKey(
                                            on_delete=django.db.models.deletion.PROTECT,
                                            related_name="jars",
                                            to=settings.AUTH_USER_MODEL,
                                         )),
                ("creator_wallet",       models.CharField(
                                            db_index=True, max_length=42,
                                            validators=[apps.jars.validators.validate_wallet_address],
                                         )),
                ("title",                models.CharField(db_index=True, max_length=120)),
                ("description",          models.TextField(max_length=1000)),
                ("category",             models.CharField(
                                            choices=[
                                                ("humanitarian","Humanitarian"),("technology","Technology"),
                                                ("education","Education"),("environment","Environment"),
                                                ("healthcare","Healthcare"),("gaming","Gaming"),
                                                ("arts","Arts & Culture"),("community","Community"),
                                                ("research","Research"),("other","Other"),
                                            ],
                                            db_index=True, default="other", max_length=20,
                                         )),
                ("cover_emoji",          models.CharField(default="🫙", max_length=8)),
                ("cover_image_url",      models.URLField(blank=True, default="")),
                ("target_amount_matic",  models.DecimalField(
                                            decimal_places=6, max_digits=20,
                                            validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))],
                                         )),
                ("amount_raised_matic",  models.DecimalField(
                                            decimal_places=6, default=decimal.Decimal("0.000000"),
                                            max_digits=20,
                                            validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))],
                                         )),
                ("deadline",             models.DateTimeField(
                                            db_index=True,
                                            validators=[apps.jars.validators.validate_future_deadline],
                                         )),
                ("status",               models.CharField(
                                            choices=[
                                                ("active","Active"),("completed","Completed"),
                                                ("expired","Expired"),("withdrawn","Withdrawn"),
                                            ],
                                            db_index=True, default="active", max_length=12,
                                         )),
                ("creation_tx_hash",     models.CharField(blank=True, db_index=True, default="", max_length=66)),
                ("is_verified_on_chain", models.BooleanField(db_index=True, default=False)),
                ("donor_count",          models.PositiveIntegerField(default=0)),
                ("created_at",           models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at",           models.DateTimeField(auto_now=True)),
                ("withdrawn_at",         models.DateTimeField(blank=True, null=True)),
                ("withdrawal_tx_hash",   models.CharField(blank=True, default="", max_length=66)),
            ],
            options={
                "verbose_name":        "Jar",
                "verbose_name_plural": "Jars",
                "db_table":            "jars_jar",
                "ordering":            ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="jar",
            index=models.Index(fields=["status", "deadline"],       name="idx_jar_status_deadline"),
        ),
        migrations.AddIndex(
            model_name="jar",
            index=models.Index(fields=["creator_wallet", "status"], name="idx_jar_creator_status"),
        ),
        migrations.AddIndex(
            model_name="jar",
            index=models.Index(fields=["category", "status"],       name="idx_jar_category_status"),
        ),
        migrations.AddIndex(
            model_name="jar",
            index=models.Index(fields=["is_verified_on_chain"],     name="idx_jar_verified"),
        ),
        migrations.AddConstraint(
            model_name="jar",
            constraint=models.CheckConstraint(
                check=models.Q(amount_raised_matic__gte=0),
                name="chk_jar_raised_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="jar",
            constraint=models.CheckConstraint(
                check=models.Q(target_amount_matic__gte=decimal.Decimal("0.01")),
                name="chk_jar_target_min",
            ),
        ),
    ]

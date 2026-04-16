"""
API test suite for JarFund backend.

Run with:
    pytest tests/test_api.py -v
    pytest tests/test_api.py -v --tb=short -x   # stop on first failure
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

# ─────────────────────────────────────────────────────────────────
#  FIXTURES
# ─────────────────────────────────────────────────────────────────

TEST_WALLET_1 = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"
TEST_WALLET_2 = "0x2b5AD5c4795c026514f8317c7a215E218DcCD6cF"
TEST_TX_HASH  = "0x" + "a" * 64
TEST_TX_HASH2 = "0x" + "b" * 64


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user1(db):
    return User.objects.create(
        wallet_address=TEST_WALLET_1,
        username="alice",
        is_verified=True,
    )


@pytest.fixture
def user2(db):
    return User.objects.create(
        wallet_address=TEST_WALLET_2,
        username="bob",
        is_verified=True,
    )


@pytest.fixture
def auth_client(api_client, user1):
    """APIClient authenticated as user1."""
    refresh = RefreshToken.for_user(user1)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return api_client


@pytest.fixture
def auth_client2(api_client, user2):
    """APIClient authenticated as user2."""
    refresh = RefreshToken.for_user(user2)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return api_client


@pytest.fixture
def active_jar(db, user1):
    from apps.jars.models import Jar, JarStatus
    return Jar.objects.create(
        creator=user1,
        creator_wallet=TEST_WALLET_1,
        title="Test Jar",
        description="A test fundraiser",
        category="education",
        target_amount_matic=Decimal("100.0"),
        deadline=timezone.now() + timezone.timedelta(days=7),
        status=JarStatus.ACTIVE,
    )


@pytest.fixture
def confirmed_donation(db, active_jar, user2):
    from apps.donations.models import Donation, TxStatus
    return Donation.objects.create(
        jar=active_jar,
        donor=user2,
        donor_wallet=TEST_WALLET_2,
        amount_matic=Decimal("10.0"),
        amount_wei="10000000000000000000",
        tx_hash=TEST_TX_HASH,
        tx_status=TxStatus.CONFIRMED,
        is_verified=True,
        confirmations=5,
    )


# ─────────────────────────────────────────────────────────────────
#  AUTH TESTS
# ─────────────────────────────────────────────────────────────────

class TestNonce:
    def test_get_nonce_creates_user(self, api_client, db):
        resp = api_client.get("/api/v1/auth/nonce/", {"wallet": TEST_WALLET_1})
        assert resp.status_code == status.HTTP_200_OK
        assert "nonce" in resp.data
        assert "message" in resp.data
        assert resp.data["wallet"] == TEST_WALLET_1
        assert User.objects.filter(wallet_address=TEST_WALLET_1).exists()

    def test_get_nonce_existing_user(self, api_client, user1):
        resp = api_client.get("/api/v1/auth/nonce/", {"wallet": TEST_WALLET_1})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["nonce"] == user1.nonce

    def test_get_nonce_invalid_wallet(self, api_client, db):
        resp = api_client.get("/api/v1/auth/nonce/", {"wallet": "not-an-address"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_nonce_missing_wallet(self, api_client, db):
        resp = api_client.get("/api/v1/auth/nonce/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestWalletVerify:
    @patch("apps.users.serializers.Account.recover_message")
    def test_verify_success(self, mock_recover, api_client, user1):
        mock_recover.return_value = TEST_WALLET_1
        old_nonce = user1.nonce

        resp = api_client.post("/api/v1/auth/verify/", {
            "wallet":    TEST_WALLET_1,
            "signature": "0x" + "f" * 130,
        })

        assert resp.status_code == status.HTTP_200_OK
        assert "access"  in resp.data["data"]
        assert "refresh" in resp.data["data"]
        assert "user"    in resp.data["data"]

        # Nonce should have rotated
        user1.refresh_from_db()
        assert user1.nonce != old_nonce

    @patch("apps.users.serializers.Account.recover_message")
    def test_verify_wrong_signer(self, mock_recover, api_client, user1):
        # Signature recovers a DIFFERENT address
        mock_recover.return_value = TEST_WALLET_2
        resp = api_client.post("/api/v1/auth/verify/", {
            "wallet":    TEST_WALLET_1,
            "signature": "0x" + "f" * 130,
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_bad_signature_format(self, api_client, user1):
        resp = api_client.post("/api/v1/auth/verify/", {
            "wallet":    TEST_WALLET_1,
            "signature": "not-a-signature",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestProfile:
    def test_get_profile_authenticated(self, auth_client, user1):
        resp = auth_client.get("/api/v1/auth/profile/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["wallet_address"] == TEST_WALLET_1

    def test_get_profile_unauthenticated(self, api_client):
        resp = api_client.get("/api/v1/auth/profile/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_profile(self, auth_client, user1):
        resp = auth_client.patch("/api/v1/auth/profile/", {"username": "alice_updated"})
        assert resp.status_code == status.HTTP_200_OK
        user1.refresh_from_db()
        assert user1.username == "alice_updated"


# ─────────────────────────────────────────────────────────────────
#  JAR TESTS
# ─────────────────────────────────────────────────────────────────

class TestJarList:
    def test_list_public(self, api_client, active_jar):
        resp = api_client.get("/api/v1/jars/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_list_filter_status(self, api_client, active_jar):
        resp = api_client.get("/api/v1/jars/", {"status": "active"})
        assert resp.status_code == status.HTTP_200_OK
        for result in resp.data["results"]:
            assert result["status"] == "active"

    def test_list_search(self, api_client, active_jar):
        resp = api_client.get("/api/v1/jars/", {"search": "Test Jar"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1


class TestJarCreate:
    def test_create_jar_authenticated(self, auth_client):
        resp = auth_client.post("/api/v1/jars/", {
            "title":               "My Campaign",
            "description":         "Test description",
            "category":            "education",
            "target_amount_matic": "50.0",
            "deadline":            (timezone.now() + timezone.timedelta(days=7)).isoformat(),
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["title"] == "My Campaign"

    def test_create_jar_unauthenticated(self, api_client):
        resp = api_client.post("/api/v1/jars/", {"title": "test"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_jar_past_deadline(self, auth_client):
        resp = auth_client.post("/api/v1/jars/", {
            "title":               "Bad Jar",
            "description":         "desc",
            "category":            "other",
            "target_amount_matic": "10.0",
            "deadline":            (timezone.now() - timezone.timedelta(hours=1)).isoformat(),
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_jar_target_too_low(self, auth_client):
        resp = auth_client.post("/api/v1/jars/", {
            "title":               "Tiny Jar",
            "description":         "desc",
            "category":            "other",
            "target_amount_matic": "0.001",
            "deadline":            (timezone.now() + timezone.timedelta(days=2)).isoformat(),
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestJarDetail:
    def test_get_detail_public(self, api_client, active_jar):
        resp = api_client.get(f"/api/v1/jars/{active_jar.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert "donations" in resp.data

    def test_get_detail_not_found(self, api_client):
        resp = api_client.get("/api/v1/jars/99999/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestJarUpdate:
    def test_creator_can_update(self, auth_client, active_jar):
        resp = auth_client.patch(f"/api/v1/jars/{active_jar.id}/", {"title": "Updated Title"})
        assert resp.status_code == status.HTTP_200_OK
        active_jar.refresh_from_db()
        assert active_jar.title == "Updated Title"

    def test_non_creator_cannot_update(self, auth_client2, active_jar):
        resp = auth_client2.patch(f"/api/v1/jars/{active_jar.id}/", {"title": "Hacked"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestJarWithdraw:
    def test_withdraw_conditions_not_met(self, auth_client, active_jar):
        resp = auth_client.post(
            f"/api/v1/jars/{active_jar.id}/withdraw/",
            {"withdrawal_tx_hash": "0x" + "c" * 64},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_withdraw_after_deadline(self, auth_client, active_jar, confirmed_donation):
        # Expire the jar
        from apps.jars.models import JarStatus
        active_jar.deadline = timezone.now() - timezone.timedelta(hours=1)
        active_jar.save()
        active_jar.sync_status()

        resp = auth_client.post(
            f"/api/v1/jars/{active_jar.id}/withdraw/",
            {"withdrawal_tx_hash": "0x" + "c" * 64},
        )
        assert resp.status_code == status.HTTP_200_OK
        active_jar.refresh_from_db()
        assert active_jar.status == JarStatus.WITHDRAWN

    def test_non_creator_cannot_withdraw(self, auth_client2, active_jar):
        resp = auth_client2.post(
            f"/api/v1/jars/{active_jar.id}/withdraw/",
            {"withdrawal_tx_hash": "0x" + "c" * 64},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ─────────────────────────────────────────────────────────────────
#  DONATION TESTS
# ─────────────────────────────────────────────────────────────────

class TestDonationCreate:
    @patch("apps.blockchain.tasks.verify_single_transaction.apply_async")
    def test_create_donation(self, mock_task, auth_client2, active_jar):
        resp = auth_client2.post("/api/v1/donations/", {
            "jar_id":       active_jar.id,
            "donor_wallet": TEST_WALLET_2,
            "amount_matic": "5.0",
            "amount_wei":   "5000000000000000000",
            "tx_hash":      TEST_TX_HASH,
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["tx_status"] == "pending"
        mock_task.assert_called_once()

    def test_creator_cannot_donate_to_own_jar(self, auth_client, active_jar):
        resp = auth_client.post("/api/v1/donations/", {
            "jar_id":       active_jar.id,
            "donor_wallet": TEST_WALLET_1,
            "amount_matic": "5.0",
            "amount_wei":   "5000000000000000000",
            "tx_hash":      TEST_TX_HASH,
        })
        assert resp.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]

    def test_wallet_mismatch_rejected(self, auth_client2, active_jar):
        """User2 tries to submit a donation with User1's wallet address."""
        resp = auth_client2.post("/api/v1/donations/", {
            "jar_id":       active_jar.id,
            "donor_wallet": TEST_WALLET_1,   # <-- wrong wallet
            "amount_matic": "5.0",
            "amount_wei":   "5000000000000000000",
            "tx_hash":      TEST_TX_HASH,
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_duplicate_tx_hash_rejected(self, auth_client2, active_jar, confirmed_donation):
        resp = auth_client2.post("/api/v1/donations/", {
            "jar_id":       active_jar.id,
            "donor_wallet": TEST_WALLET_2,
            "amount_matic": "5.0",
            "amount_wei":   "5000000000000000000",
            "tx_hash":      TEST_TX_HASH,  # already recorded
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestDonationList:
    def test_list_by_jar(self, api_client, confirmed_donation, active_jar):
        resp = api_client.get("/api/v1/donations/", {"jar_id": active_jar.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_my_donations_authenticated(self, auth_client2, confirmed_donation):
        resp = auth_client2.get("/api/v1/donations/my/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1
        assert "stats" in resp.data

    def test_my_donations_unauthenticated(self, api_client):
        resp = api_client.get("/api/v1/donations/my/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────────────────────────────────────────────────────
#  BLOCKCHAIN TESTS
# ─────────────────────────────────────────────────────────────────

class TestPlatformStats:
    def test_stats_public(self, api_client, confirmed_donation):
        resp = api_client.get("/api/v1/blockchain/stats/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert "total_jars"        in data
        assert "total_raised_matic" in data
        assert "total_donors"      in data

    def test_stats_cached(self, api_client, db):
        from django.core.cache import cache
        cache.set("jarfund_platform_stats", {"total_jars": 99}, 60)
        resp = api_client.get("/api/v1/blockchain/stats/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["cached"] is True
        assert resp.data["data"]["total_jars"] == 99


class TestTxVerify:
    @patch("apps.blockchain.tasks.verify_single_transaction.apply_async")
    def test_verify_queues_task(self, mock_task, api_client, confirmed_donation):
        resp = api_client.post("/api/v1/blockchain/verify/", {"tx_hash": TEST_TX_HASH})
        assert resp.status_code == status.HTTP_200_OK
        mock_task.assert_called_once()

    def test_verify_invalid_hash(self, api_client):
        resp = api_client.post("/api/v1/blockchain/verify/", {"tx_hash": "0xshort"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestHealthCheck:
    def test_health_ok(self, api_client, db):
        resp = api_client.get("/health/")
        assert resp.status_code in [200, 503]
        assert "status" in resp.data
        assert "checks" in resp.data

"""Exercise authentication, transport failures, and exact command contracts."""
import asyncio
import importlib.util
import pathlib
import sys
import time
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Test the independent client without importing Home Assistant's setup module.
package = types.ModuleType("tohmo_client_test")
package.__path__ = [str(ROOT / "custom_components" / "tohmo")]
sys.modules[package.__name__] = package
from tohmo_client_test.api import (  # noqa: E402
    ApiError, AuthenticationError, ConnectionError, TohmoClient, TohmoError, segment,
)


class Response:
    def __init__(self, status=200, body=None, headers=None):
        self.status, self.body, self.headers = status, body, headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def token(**updates):
    return {"access_token": "old-access", "refresh_token": "old-refresh",
            "expires_at": time.time() + 3600, **updates}


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_does_not_retain_password(self):
        saved = []
        session = Session([Response(body={"access_token": "access", "refresh_token": "refresh", "expires_in": 3600})])
        client = TohmoClient(session, on_tokens=saved.append)
        await client.login("example@example.invalid", "private-password")
        self.assertNotIn("private-password", repr(client.__dict__ | {"_session": None}))
        self.assertEqual(saved[0]["refresh_token"], "refresh")
        self.assertFalse(session.calls[0][2]["allow_redirects"])

    async def test_concurrent_expiry_refreshes_once(self):
        saved = []
        session = Session([Response(body={"access_token": "new-access", "refresh_token": "rotated", "expires_in": 3600}), Response(body={"data": []}), Response(body={"data": []})])
        client = TohmoClient(session, token(expires_at=0), saved.append)
        await asyncio.gather(client.charge_points(), client.charge_points())
        self.assertEqual([call[0] for call in session.calls], ["POST", "GET", "GET"])
        self.assertEqual(len(saved), 1)

    async def test_read_401_refreshes_and_retries_once(self):
        session = Session([Response(401), Response(body={"access_token": "new", "expires_in": 3600}), Response(body={"data": []})])
        client = TohmoClient(session, token())
        self.assertEqual(await client.charge_points(), [])
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(client.tokens["refresh_token"], "old-refresh")

    async def test_mutation_401_is_never_replayed(self):
        session = Session([Response(401)])
        with self.assertRaises(AuthenticationError):
            await TohmoClient(session, token()).start(42)
        self.assertEqual(len(session.calls), 1)

    async def test_timeout_does_not_replay_or_leak(self):
        session = Session([TimeoutError("token=private")])
        with self.assertRaises(ConnectionError) as error:
            await TohmoClient(session, token()).stop("session/one")
        self.assertNotIn("private", str(error.exception))
        self.assertEqual(len(session.calls), 1)
        self.assertTrue(session.calls[0][1].endswith("/session/session%2Fone/end"))

    async def test_success_false_is_failure(self):
        session = Session([Response(body={"success": False, "message": "private-data"})])
        with self.assertRaises(ApiError) as error:
            await TohmoClient(session, token()).reboot(1)
        self.assertNotIn("private-data", str(error.exception))

    async def test_rate_limit_blocks_further_requests(self):
        session = Session([Response(429, headers={"Retry-After": "120"})])
        client = TohmoClient(session, token())
        for _ in range(2):
            with self.assertRaises(ApiError):
                await client.charge_points()
        self.assertEqual(len(session.calls), 1)

    async def test_exact_start_stop_unlock_contracts(self):
        session = Session([Response(204), Response(204), Response(204)])
        client = TohmoClient(session, token())
        await client.start("42")
        await client.stop("session-1")
        await client.unlock("cp-1", 42)
        self.assertEqual(session.calls[0][2]["json"], {"evseId": 42})
        self.assertTrue(session.calls[1][1].endswith("/session/session-1/end"))
        self.assertTrue(session.calls[2][1].endswith("/personal/charge-point/cp-1/unlock-connector/42"))
        self.assertEqual(segment("ES*TEST*E123"), "ES%2ATEST%2AE123")

    async def test_invalid_tokens_fail_before_storage(self):
        for access, expiry in (("", 3600), ("a", "nan"), ("a", "inf"), ("a", -1)):
            saved = []
            session = Session([Response(body={"access_token": access, "refresh_token": "r", "expires_in": expiry})])
            client = TohmoClient(session, on_tokens=saved.append)
            with self.assertRaises(AuthenticationError):
                await client.login("example@example.invalid", "test-password")
            self.assertEqual(saved, [])

    async def test_alphanumeric_identifier_never_sent_as_internal_id(self):
        session = Session([])
        with self.assertRaises(TohmoError):
            await TohmoClient(session, token()).start("ES*TEST*E123")
        self.assertEqual(session.calls, [])

    async def test_invalid_charger_shape_fails_closed(self):
        session = Session([Response(body={"data": {"id": 12}})])
        with self.assertRaises(ConnectionError):
            await TohmoClient(session, token()).charge_points()


if __name__ == "__main__":
    unittest.main()

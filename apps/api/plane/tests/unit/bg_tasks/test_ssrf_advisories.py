# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Per-advisory SSRF regression tests.

Each test reproduces a published / reported SSRF advisory scenario and asserts
the current code blocks it. This file is the auditable map of "which advisory is
covered where"; the lower-level mechanics (IP classification, pinning, redirect
re-validation) are exercised in detail in ``test_url_security.py`` and
``test_work_item_link_task.py``.

Advisory coverage
-----------------
URL validation and pinned fetching
  * GHSA-m3f8-q4wj-9grv / CVE-2026-30242 / GHSA-75vf-hh93-h7mx
        private/metadata/loopback URL rejection                       -> TestValidateUrl
  * GHSA-75fg-f8qg-23wv  CGNAT(100.64/10), 6to4, multicast missed     -> TestValidateUrl
  * GHSA-whh3-5g95-4qhc / -4mjx-q738-87cf / -6p39-x6q9-h3g5 /
    -9292-pvg4-7hvm / -fgcv-6h3f-xcx9  DNS-rebinding TOCTOU            -> TestPinnedFetchRebinding
  * GHSA-6v37-328w-j2wv / -jw6g-h7h5-rfc6 / -mq87-52pf-hm3h
        SSRF via HTTP redirect following                              -> TestPinnedFetchRedirect

Work-item link unfurling / favicon
  * GHSA-8wvv-p676-hcw4 / -fv24-3845-646g / -9292-pvg4-7hvm  link rebinding
  * GHSA-9fr2-pprw-pp9j / CVE-2026-39843  favicon redirect SSRF        -> TestFaviconRedirect
  * GHSA-3856-6mgg-rx84  favicon DNS-rebinding                         -> TestFaviconRebinding

OAuth avatar
  * GHSA-cv9p-325g-wmv5  OAuth avatar redirect SSRF -> static-asset exfil
  * GHSA-hx79-5pj5-qh42  OAuth avatar SSRF (avatar hop)                -> TestOAuthAvatarSSRF
"""

import pytest
import requests
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from plane.utils.ip_address import validate_url
from plane.bgtasks.work_item_link_task import fetch_and_encode_favicon, DEFAULT_FAVICON
from plane.authentication.adapter.base import Adapter


def _addr(ip):
    family = 6 if ":" in ip else 2
    return (family, None, None, None, (ip, 0))


def _resp(status_code=200, headers=None, content=b"OK"):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.content = content
    return resp


_BLOCKED = "Access to private/internal networks is not allowed"


# ---------------------------------------------------------------------------
# URL validation
# GHSA-m3f8-q4wj-9grv / CVE-2026-30242 / GHSA-75vf-hh93-h7mx / GHSA-75fg-f8qg-23wv
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestValidateUrl:
    @pytest.mark.parametrize(
        "ip",
        [
            "169.254.169.254",  # AWS/GCP metadata (CVE-2026-30242 PoC)
            "127.0.0.1",        # loopback
            "10.0.0.1",         # private
            "172.16.0.1",       # private
            "192.168.0.1",      # private
            "::1",              # IPv6 loopback
            "100.64.0.1",       # CGNAT / RFC 6598 (GHSA-75fg)
            "2002:7f00:1::",    # 6to4 -> 127.0.0.1 (GHSA-75fg)
            "224.0.0.1",        # multicast (GHSA-75fg)
            "::ffff:169.254.169.254",  # IPv4-mapped metadata
        ],
    )
    def test_internal_url_is_rejected(self, ip):
        with patch("plane.utils.ip_address.socket.getaddrinfo") as dns:
            dns.return_value = [_addr(ip)]
            with pytest.raises(ValueError, match="private/internal"):
                validate_url(
                    "https://attacker.example.com/resource",
                )

    def test_public_url_passes(self):
        with patch("plane.utils.ip_address.socket.getaddrinfo") as dns:
            dns.return_value = [_addr("93.184.216.34")]
            # Should not raise
            validate_url("https://public.example.com/x")


# ---------------------------------------------------------------------------
# DNS-rebinding TOCTOU
# GHSA-whh3-5g95-4qhc / -4mjx-q738-87cf / -6p39-x6q9-h3g5 / -9292 / -fgcv
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPinnedFetchRebinding:
    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_connection_pinned_to_validated_ip(self, mock_resolve, mock_session_cls):
        from plane.utils.url_security import pinned_fetch

        # The validator resolves to a public IP; the connection must go to THAT
        # IP literal, so a rebind to an internal IP after validation is moot.
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        pinned_fetch("POST", "https://rebinder.example.com/hook", json={})

        _, url = session.request.call_args.args
        assert url == "https://93.184.216.34:443/hook"  # IP literal -> no 2nd DNS lookup

    @patch("plane.utils.url_security.resolve_and_validate")
    def test_rebind_to_internal_is_blocked(self, mock_resolve):
        from plane.utils.url_security import pinned_fetch

        mock_resolve.side_effect = ValueError(_BLOCKED)
        with pytest.raises(ValueError, match="private/internal"):
            pinned_fetch("POST", "https://rebinder.example.com/hook", json={})


# ---------------------------------------------------------------------------
# SSRF via HTTP redirect following
# GHSA-6v37-328w-j2wv / GHSA-jw6g-h7h5-rfc6 / GHSA-mq87-52pf-hm3h
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPinnedFetchRedirect:
    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_pinned_fetch_does_not_follow_redirects(self, mock_resolve, mock_session_cls):
        from plane.utils.url_security import pinned_fetch

        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        # The endpoint replies 302 -> internal; pinned_fetch must not follow.
        session.request.return_value = _resp(
            302, headers={"Location": "http://169.254.169.254/latest/meta-data/"}
        )

        resp = pinned_fetch("POST", "https://endpoint.example.com/x", json={})

        # The 3xx is returned as-is and only ONE request was made (no follow).
        assert resp.status_code == 302
        assert session.request.call_count == 1
        assert session.request.call_args.kwargs["allow_redirects"] is False


# ---------------------------------------------------------------------------
# Favicon redirect SSRF — GHSA-9fr2-pprw-pp9j / CVE-2026-39843
# A <link rel=icon> whose href is public but 30x-redirects to a private IP must
# NOT exfiltrate internal content; the favicon falls back to the default icon.
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestFaviconRedirect:
    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    @patch("plane.bgtasks.work_item_link_task.socket.getaddrinfo")
    def test_favicon_redirect_to_private_returns_default(
        self, mock_pre_dns, mock_resolve, mock_session_cls
    ):
        # validate_url_ip pre-check (work_item_link_task.socket) sees a public IP.
        mock_pre_dns.return_value = [_addr("93.184.216.34")]
        # safe_get: hop0 public, hop1 (redirect target) blocked.
        mock_resolve.side_effect = [["93.184.216.34"], ValueError(_BLOCKED)]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(
            302, headers={"Location": "http://192.168.8.14:8081/"}
        )

        soup = BeautifulSoup(
            '<link rel="icon" href="https://redirector.example.com/x">',
            "html.parser",
        )
        result = fetch_and_encode_favicon({}, soup, "https://attacker.example.com")

        # Blocked -> default icon, NOT the internal response body.
        assert result["favicon_base64"] == f"data:image/svg+xml;base64,{DEFAULT_FAVICON}"


# ---------------------------------------------------------------------------
# Favicon DNS rebinding — GHSA-3856-6mgg-rx84
# The favicon host passes the pre-check (public) but resolves to a private IP at
# fetch time; the pinned client re-resolves+validates and blocks it.
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestFaviconRebinding:
    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    @patch("plane.bgtasks.work_item_link_task.socket.getaddrinfo")
    def test_favicon_rebind_to_private_returns_default(
        self, mock_pre_dns, mock_resolve, mock_session_cls
    ):
        mock_pre_dns.return_value = [_addr("93.184.216.34")]  # pre-check: public
        mock_resolve.side_effect = ValueError(_BLOCKED)        # fetch-time: rebound -> blocked
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        soup = BeautifulSoup(
            '<link rel="icon" href="http://rebind.example.com:8443/">',
            "html.parser",
        )
        result = fetch_and_encode_favicon({}, soup, "https://attacker.example.com")
        assert result["favicon_base64"] == f"data:image/svg+xml;base64,{DEFAULT_FAVICON}"


# ---------------------------------------------------------------------------
# OAuth avatar SSRF — GHSA-cv9p-325g-wmv5 / GHSA-hx79-5pj5-qh42 (avatar hop)
# download_and_upload_avatar must reject avatar URLs that point at, or redirect
# to, internal addresses, returning None (no fetch stored as an asset).
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestOAuthAvatarSSRF:
    def _adapter(self):
        return Adapter(request=MagicMock(), provider="github")

    @patch("plane.utils.url_security.resolve_and_validate")
    def test_avatar_to_internal_ip_is_blocked(self, mock_resolve):
        mock_resolve.side_effect = ValueError(_BLOCKED)
        result = self._adapter().download_and_upload_avatar(
            "http://169.254.169.254/latest/meta-data/", user=MagicMock()
        )
        assert result is None
        mock_resolve.assert_called()  # SSRF validation was actually attempted

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_avatar_redirect_to_internal_is_blocked(self, mock_resolve, mock_session_cls):
        # Public avatar URL that 302-redirects to the metadata service.
        mock_resolve.side_effect = [["93.184.216.34"], ValueError(_BLOCKED)]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(
            302, headers={"Location": "http://169.254.169.254/imds"}
        )
        result = self._adapter().download_and_upload_avatar(
            "https://evil.example.com/avatar", user=MagicMock()
        )
        assert result is None

    @patch("plane.authentication.adapter.base.pinned_fetch_following_redirects")
    def test_avatar_uses_ssrf_safe_client(self, mock_fetch):
        # Wiring guard: the avatar path must go through the pinned client, never
        # a raw requests.get (which would re-resolve + follow redirects freely).
        mock_fetch.side_effect = ValueError(_BLOCKED)
        result = self._adapter().download_and_upload_avatar(
            "https://cdn.example.com/a.png", user=MagicMock()
        )
        assert result is None
        assert mock_fetch.call_args.args[0] == "GET"
        assert mock_fetch.call_args.args[1] == "https://cdn.example.com/a.png"

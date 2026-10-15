"""Small GitHub REST client using existing Git authentication, never logging credentials."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.error
import urllib.request

REPO = "WalidAbdelmeguid/HireGuard"


class GitHubError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHub:
    def __init__(self):
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            self.authorization = f"Bearer {token}"
        else:
            process = subprocess.run(
                ["git", "credential", "fill"],
                input="protocol=https\nhost=github.com\n\n",
                text=True,
                capture_output=True,
                check=False,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"},
            )
            fields = dict(line.split("=", 1) for line in process.stdout.splitlines() if "=" in line)
            if process.returncode or not fields.get("password"):
                raise GitHubError(
                    "GitHub authentication unavailable; use gh auth or existing Git credentials"
                )
            value = f"{fields.get('username', 'git')}:{fields['password']}".encode()
            self.authorization = "Basic " + base64.b64encode(value).decode()
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, path, payload=None):
        if not path.startswith(f"/repos/{REPO}") and path != "/user":
            raise GitHubError("GitHub request outside the authorized repository")
        request = urllib.request.Request(
            "https://api.github.com" + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            method=method,
            headers={
                "Authorization": self.authorization,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "HireGuard-M1-tooling",
            },
        )
        try:
            with self.opener.open(request, timeout=30) as response:
                body = response.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            raise GitHubError(
                f"GitHub {method} {path.split('?')[0]} returned HTTP {exc.code}"
            ) from None
        except urllib.error.URLError:
            raise GitHubError("GitHub connection failed") from None

    def pages(self, path):
        separator = "&" if "?" in path else "?"
        page = 1
        result = []
        while True:
            batch = self.request("GET", f"{path}{separator}per_page=100&page={page}")
            result.extend(batch)
            if len(batch) < 100:
                return result
            page += 1

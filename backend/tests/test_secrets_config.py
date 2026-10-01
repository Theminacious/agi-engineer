"""Secret handling, startup validation, and credential-leak regression tests."""

import base64
import logging

import pytest

from app.config import Settings, SettingsValidationError


def _prod_kwargs(**overrides):
    base = dict(
        api_env="production",
        jwt_secret_key="jwt-secret",
        webhook_secret="wh-secret",
        github_client_secret="client-secret",
        github_app_private_key="private-key",
    )
    base.update(overrides)
    return base


def test_missing_production_secret_fails_startup():
    with pytest.raises(SettingsValidationError) as exc:
        Settings(_env_file=None, **_prod_kwargs(jwt_secret_key=""))
    assert "jwt_secret_key" in str(exc.value)


def test_all_missing_production_secrets_reported():
    with pytest.raises(SettingsValidationError) as exc:
        Settings(
            _env_file=None,
            api_env="production",
            jwt_secret_key="",
            webhook_secret="",
            github_client_secret="",
            github_app_private_key="",
        )
    message = str(exc.value)
    for field in ("jwt_secret_key", "webhook_secret", "github_client_secret", "github_app_private_key"):
        assert field in message


def test_valid_production_configuration_starts():
    settings = Settings(_env_file=None, **_prod_kwargs())
    assert settings.is_production
    assert settings.missing_required_secrets() == []


def test_development_allows_empty_secrets():
    settings = Settings(_env_file=None, api_env="development")
    assert not settings.is_production
    assert settings.jwt_secret_key == ""


def test_safe_dict_masks_secrets():
    settings = Settings(_env_file=None, **_prod_kwargs(github_token="ghs_realtoken"))
    safe = settings.safe_dict()
    assert safe["jwt_secret_key"] == "***REDACTED***"
    assert safe["webhook_secret"] == "***REDACTED***"
    assert safe["github_app_private_key"] == "***REDACTED***"
    assert safe["github_token"] == "***REDACTED***"
    assert safe["api_env"] == "production"


def test_repr_never_exposes_secret_values():
    settings = Settings(_env_file=None, **_prod_kwargs(jwt_secret_key="super-secret-value"))
    text = repr(settings)
    assert "super-secret-value" not in text
    assert "***REDACTED***" in text


def test_oauth_exchange_never_logs_token(monkeypatch, caplog):
    import app.security as security

    token = "gho_SECRETACCESSTOKEN123"

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"access_token": token, "token_type": "bearer"}

    monkeypatch.setattr(security.requests, "post", lambda *a, **k: _Resp())
    with caplog.at_level(logging.DEBUG):
        data = security.GitHubOAuthManager.exchange_code_for_token("code123")

    assert data["access_token"] == token
    assert token not in caplog.text
    assert "bearer" not in caplog.text.lower()


def test_oauth_exchange_failure_does_not_log_response_body(monkeypatch, caplog):
    import app.security as security

    leaked = "gho_LEAKEDINBODY"

    class _Resp:
        status_code = 401
        text = f'{{"access_token": "{leaked}"}}'

        @staticmethod
        def json():
            return {}

    monkeypatch.setattr(security.requests, "post", lambda *a, **k: _Resp())
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ValueError) as exc:
            security.GitHubOAuthManager.exchange_code_for_token("code123")

    assert leaked not in caplog.text
    assert leaked not in str(exc.value)


def test_git_credentials_use_header_not_token_url():
    from app.security import git_credential_config_args

    token = "ghs_INSTALLTOKEN"
    args = git_credential_config_args(token)

    assert args[0] == "-c"
    assert args[1].startswith("http.extraheader=Authorization: Basic ")
    assert f"x-access-token:{token}@" not in " ".join(args)
    encoded = args[1].split("Basic ", 1)[1]
    assert base64.b64decode(encoded).decode() == f"x-access-token:{token}"


def test_clone_remote_url_is_tokenless(monkeypatch):
    from app.services.github_service import GitHubService

    token = "ghs_PERSISTEDTOKEN"
    calls = []

    service = GitHubService()
    monkeypatch.setattr(service, "get_installation_token", lambda _id: token)

    import subprocess

    class _Done:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(args, *a, **k):
        calls.append(list(args))
        return _Done()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    monkeypatch.setattr("os.makedirs", lambda *a, **k: None)

    ok = service.clone_repository(1, "owner/repo", "abc123", "/tmp/agi-clone-test")
    assert ok

    joined = [" ".join(a) for a in calls]
    for line in joined:
        assert f"x-access-token:{token}@" not in line
        assert token not in line.replace(
            base64.b64encode(f"x-access-token:{token}".encode()).decode(), ""
        )

    remote_add = next(a for a in calls if "remote" in a and "add" in a)
    assert remote_add[-1] == "https://github.com/owner/repo.git"

"""No Cloudflare account is touched by these instructions."""
import pytest

from miseport.merchant_onboarding import (
    DeploymentGuideError, merchant_deploy_guide,
)


def test_guide_uses_exact_merchant_domain_and_no_upload():
    guide = merchant_deploy_guide("https://tea.pages.dev")
    assert guide.health_url == "https://tea.pages.dev/healthz"
    assert guide.mcp_url == "https://tea.pages.dev/mcp"
    assert guide.json_url == "https://tea.pages.dev/catalog.json"
    assert guide.dashboard_url == "https://dash.cloudflare.com/"
    assert "direct-upload" in guide.docs_url
    assert len(guide.steps_ja) == 6
    assert "APIキー" in "\n".join(guide.steps_ja)
    assert "MisePortは自動でアップロードしません" in "\n".join(guide.steps_ja)
    assert "MCP接続成功" in "\n".join(guide.steps_ja)
    assert "公開予定" in guide.copy_summary()
    assert "https://tea.pages.dev/mcp" in guide.copy_summary()


@pytest.mark.parametrize("bad", [
    "", "https://", "http://tea.pages.dev", "https://tea.pages.dev/",
    "https://tea.pages.dev?q=1", "https://tea.pages.dev/path",
    "https://user:secret@tea.pages.dev", "https://127.0.0.1",
    "https://localhost", "https://10.1.1.1", "https://tea.local",
    "https://tea.pages.dev:8080", "https://tea.pages.dev#x",
    "https://tea.pages.dev\\nhttps://evil.example",
])
def test_unsafe_or_wrong_host_values_cannot_be_deploy_targets(bad):
    with pytest.raises(DeploymentGuideError):
        merchant_deploy_guide(bad)

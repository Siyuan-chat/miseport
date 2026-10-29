"""Japanese, no-credentials deployment instructions for an owner-controlled Pages URL.

No Cloudflare account access, write APIs, automatic deployment or server state.
"""
from dataclasses import dataclass
from urllib.parse import urlsplit

CLOUDFLARE_DASHBOARD = "https://dash.cloudflare.com/"
CLOUDFLARE_DIRECT_UPLOAD_DOCS = "https://developers.cloudflare.com/pages/get-started/direct-upload/"


class DeploymentGuideError(ValueError):
    pass


@dataclass(frozen=True)
class MerchantDeployGuide:
    origin: str
    dashboard_url: str
    docs_url: str
    health_url: str
    mcp_url: str
    json_url: str
    steps_ja: tuple[str, ...]

    def copy_summary(self) -> str:
        return (
            "MisePort 商店の商品データ（読み取り専用）\n"
            "公開先: " + self.origin + "\n"
            "ヘルスチェック: " + self.health_url + "\n"
            "MCP（Agent接続先）: " + self.mcp_url + "\n"
            "商品JSON: " + self.json_url + "\n"
            "注意: これは公開予定のURLです。実際のサイト公開を保証しません。\n"
        )


def merchant_deploy_guide(origin: str) -> MerchantDeployGuide:
    if type(origin) is not str or not origin or len(origin) > 2048:
        raise DeploymentGuideError("公開先のURLを入力してください。")
    try:
        parsed = urlsplit(origin)
        port = parsed.port
    except ValueError:
        raise DeploymentGuideError("公開先のURLを確認してください。") from None
    if (parsed.scheme != "https" or not parsed.hostname or port not in (None, 443)
            or origin != "https://" + parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path or "\\" in origin or any(x.isspace() for x in origin)):
        raise DeploymentGuideError("https://店舗の公開ドメイン の形式で入力してください。")
    steps = (
        "1. 商品一覧と出典・価格・公開範囲を店主自身が確認し、MisePortから商店専用ZIPを保存します。",
        "2. Cloudflareアカウントをお持ちでなければ、公式サイトでご自身のアカウントを登録します。"
        " APIキーやBASE PATをMisePortの公開サイトやCloudflare ZIPへ入れないでください。",
        "3. Cloudflare管理画面の「Workers & Pages」から「Create application」→"
        "「Get started」→「Drag and drop your files」を選びます。"
        " Direct Upload方式を選ぶと、同じプロジェクトを後からGit連携へ直接切り替えられません。",
        "4. 入力した公開ドメインと同じプロジェクト名で作成し、保存したZIPをドラッグ＆ドロップします。"
        " 画面の内容を確認して「Deploy site」を押します。MisePortは自動でアップロードしません。",
        "5. ご自身のブラウザでHTTPS公開ページ・/healthz・/api/productsを確認します。"
        " 対応するMCPクライアントで/mcpへの接続も確認します。"
        " ブラウザにページが出ることだけでは、MCP接続成功を意味しません。",
        "6. 商品を更新した場合はZIPを再生成してCloudflareで「Create a new deployment」。"
        " 公開を停止する場合はCloudflare側でプロジェクトまたは配信を停止/削除します。"
        " 以前取得された商品情報の第三者キャッシュは即時には消えないことがあります。",
    )
    return MerchantDeployGuide(
        origin=origin,
        dashboard_url=CLOUDFLARE_DASHBOARD,
        docs_url=CLOUDFLARE_DIRECT_UPLOAD_DOCS,
        health_url=origin + "/healthz",
        mcp_url=origin + "/mcp",
        json_url=origin + "/catalog.json",
        steps_ja=steps,
    )

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from datarobot_genai.drmcp import dr_mcp_tool

logger = logging.getLogger(__name__)

# エラータイプ別の対処方法データベース
ERROR_RESOLUTION_DB: dict[str, dict[str, object]] = {
    "deployment_not_found": {
        "error_pattern": r"deployment.*not found|404",
        "title": "デプロイメントが見つかりません",
        "severity": "high",
        "steps": [
            "1. デプロイメントIDが正しいか確認してください",
            "2. DataRobot UIでデプロイメントが存在するか確認",
            "3. デプロイメントが削除されていないか確認",
            "4. アクセス権限があるか確認（共有設定を確認）",
        ],
        "prevention": [
            "デプロイメントIDをコピー&ペーストで使用する",
            "削除されたデプロイメントのIDを保存しない",
        ],
    },
    "api_authentication_error": {
        "error_pattern": r"authentication|unauthorized|401|403",
        "title": "API認証エラー",
        "severity": "critical",
        "steps": [
            "1. 環境変数 DATAROBOT_API_TOKEN が正しく設定されているか確認",
            "2. API keyの有効期限を確認（DataRobot UI > API keys and tools）",
            "3. API keyが有効化されているか確認",
            "4. API keyに適切な権限があるか確認",
        ],
        "prevention": [
            "API keyの定期的なローテーション",
            "環境変数の定期確認",
        ],
    },
    "rate_limit_exceeded": {
        "error_pattern": r"rate limit|too many requests|429",
        "title": "レート制限超過",
        "severity": "medium",
        "steps": [
            "1. リクエスト頻度を下げる（バックオフ戦略を実装）",
            "2. 必要な場合はDataRobot管理者にレート制限の引き上げを依頼",
            "3. キャッシュを活用してAPI呼び出しを削減",
            "4. バッチ処理で複数のリクエストをまとめる",
        ],
        "prevention": [
            "リクエストのスロットリング実装",
            "結果のキャッシング",
        ],
    },
    "data_format_error": {
        "error_pattern": r"invalid data|format error|schema",
        "title": "データフォーマットエラー",
        "severity": "medium",
        "steps": [
            "1. 入力データのスキーマを確認",
            "2. 必須フィールドがすべて含まれているか確認",
            "3. データ型が正しいか確認（文字列、数値、日付など）",
            "4. サンプルデータでテストしてみる",
        ],
        "prevention": [
            "入力データのバリデーション実装",
            "スキーマ定義の文書化",
        ],
    },
    "timeout_error": {
        "error_pattern": r"timeout|timed out",
        "title": "タイムアウトエラー",
        "severity": "high",
        "steps": [
            "1. ネットワーク接続を確認",
            "2. タイムアウト設定を延長（大量データ処理の場合）",
            "3. データサイズを削減してリクエストを分割",
            "4. DataRobotサービスのステータスを確認",
        ],
        "prevention": [
            "適切なタイムアウト設定",
            "大量データの分割処理",
        ],
    },
    "trace_not_available": {
        "error_pattern": r"trace.*not available|no trace data",
        "title": "トレースデータが利用できません",
        "severity": "low",
        "steps": [
            "1. デプロイメント設定でトレース機能が有効か確認",
            "2. Data Explorationで予測データ保存が有効か確認",
            "3. トレースIDが正しいか確認",
            "4. トレースデータの保持期間内か確認",
        ],
        "prevention": [
            "デプロイメント作成時にトレース機能を有効化",
            "定期的なデータアーカイブ",
        ],
    },
}


@dr_mcp_tool(tags={"error", "resolution", "suggestion"})
async def suggest_error_resolution(
    error_message: str,
    deployment_id: Optional[str] = None,
    context: Optional[str] = None,
) -> str:
    """
    エラーメッセージに基づいて対処方法を提案

    Args:
        error_message: エラーメッセージ（例: "Deployment not found"）
        deployment_id: デプロイメントID（オプション、コンテキスト情報として使用）
        context: 追加のコンテキスト情報（オプション）

    Returns:
        エラー対処方法（マークダウン形式）
        - エラーの診断
        - ステップバイステップの対処手順
        - 予防策
        - 関連ドキュメントへのリンク
    """
    try:
        error_lower = error_message.lower()

        # マッチするエラータイプを検索
        matched_error = None
        for _error_type, error_info in ERROR_RESOLUTION_DB.items():
            pattern = str(error_info["error_pattern"])
            if re.search(pattern, error_lower):
                matched_error = error_info
                break

        if not matched_error:
            resolution = f"""## エラー対処提案

**エラーメッセージ**: {error_message}

このエラーは既知のパターンにマッチしませんでした。

### 一般的な対処手順
1. エラーメッセージの詳細を確認
2. DataRobotのログを確認（UIまたはAPI経由）
3. 最近の変更（デプロイメント、コード、環境変数）を確認
4. DataRobotサポートに問い合わせ

### 推奨される情報収集
- 完全なエラースタックトレース
- エラー発生時のタイムスタンプ
- デプロイメントID: {deployment_id or 'N/A'}
- 実行したリクエストの詳細"""

            return resolution

        severity_label = {
            "critical": "[CRITICAL]",
            "high": "[HIGH]",
            "medium": "[MEDIUM]",
            "low": "[LOW]",
        }

        severity = str(matched_error["severity"])

        resolution = f"""## エラー対処提案

{severity_label.get(severity, '')} **{matched_error['title']}**

**エラーメッセージ**: {error_message}
**重要度**: {severity.upper()}

### 対処手順

"""
        steps = matched_error["steps"]
        if isinstance(steps, list):
            for step in steps:
                resolution += f"{step}\n"

        resolution += "\n### 予防策\n\n"

        prevention = matched_error["prevention"]
        if isinstance(prevention, list):
            for prev in prevention:
                resolution += f"- {prev}\n"

        if deployment_id:
            resolution += f"\n### コンテキスト情報\n- **デプロイメントID**: {deployment_id}\n"

        if context:
            resolution += f"- **追加情報**: {context}\n"

        resolution += """
### 関連リソース
- DataRobot トラブルシューティングガイド
- DataRobot API リファレンス
- DataRobot サポート"""

        return resolution

    except Exception as e:
        return f"エラー対処提案の生成中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"error", "history", "resolution"})
async def get_error_resolution_history(
    deployment_id: str,
    time_range_hours: int = 168,
) -> str:
    """
    過去のエラーと対処履歴を取得

    Args:
        deployment_id: デプロイメントID
        time_range_hours: 分析対象の時間範囲（時間単位、デフォルト: 168 = 7日）

    Returns:
        エラー対処履歴（マークダウン形式）
        - 頻出エラーパターン
        - 効果的だった対処方法
        - 未解決のエラー
    """
    try:
        from app.tools.user_monitoring_tools import USER_ACTIVITY_LOG

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_range_hours)

        error_logs = [
            log
            for log in USER_ACTIVITY_LOG
            if log["deployment_id"] == deployment_id
            and log.get("error")
            and isinstance(log["timestamp"], datetime)
            and start_time <= log["timestamp"] <= end_time
        ]

        if not error_logs:
            return f"""## エラー対処履歴

**デプロイメントID**: {deployment_id}
**分析期間**: 過去 {time_range_hours} 時間

この期間中にエラーは記録されていません。"""

        # エラーを種類別に集計
        error_types: dict[str, dict[str, object]] = {}
        for log in error_logs:
            error_msg = str(log.get("error_message", "Unknown error"))
            if error_msg not in error_types:
                error_types[error_msg] = {
                    "count": 0,
                    "first_seen": log["timestamp"],
                    "last_seen": log["timestamp"],
                    "affected_users": set(),
                }
            error_types[error_msg]["count"] = (  # type: ignore[assignment]
                int(error_types[error_msg]["count"]) + 1  # type: ignore[arg-type]
            )
            ts = log["timestamp"]
            if isinstance(ts, datetime):
                last_seen = error_types[error_msg]["last_seen"]
                if isinstance(last_seen, datetime) and ts > last_seen:
                    error_types[error_msg]["last_seen"] = ts
            affected = error_types[error_msg]["affected_users"]
            if isinstance(affected, set):
                affected.add(str(log["user_id"]))

        history = f"""## エラー対処履歴

**デプロイメントID**: {deployment_id}
**分析期間**: 過去 {time_range_hours} 時間
**総エラー数**: {len(error_logs)}

### 頻出エラー TOP5

"""

        sorted_errors = sorted(
            error_types.items(), key=lambda x: int(x[1]["count"]), reverse=True  # type: ignore[arg-type]
        )[:5]

        for i, (error_msg, info) in enumerate(sorted_errors, 1):
            count = int(info["count"])  # type: ignore[arg-type]
            affected = info["affected_users"]
            affected_count = len(affected) if isinstance(affected, set) else 0
            first_seen = info["first_seen"]
            last_seen = info["last_seen"]
            first_str = (
                first_seen.strftime("%Y-%m-%d %H:%M")
                if isinstance(first_seen, datetime)
                else str(first_seen)
            )
            last_str = (
                last_seen.strftime("%Y-%m-%d %H:%M")
                if isinstance(last_seen, datetime)
                else str(last_seen)
            )

            display_msg = error_msg[:100] + ("..." if len(error_msg) > 100 else "")

            history += f"""#### {i}. {display_msg}
- **発生回数**: {count}
- **影響ユーザー数**: {affected_count}
- **初回発生**: {first_str} UTC
- **最終発生**: {last_str} UTC

"""

        history += """### 推奨アクション
- 頻出エラーについては `suggest_error_resolution` ツールで対処方法を確認
- 同じエラーが繰り返し発生している場合は根本原因の調査が必要"""

        return history

    except Exception as e:
        return f"エラー対処履歴の取得中にエラーが発生しました: {str(e)}"

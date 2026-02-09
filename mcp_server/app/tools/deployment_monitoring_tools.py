import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from datarobot.models import Deployment
from datarobot_genai.drmcp import dr_mcp_tool

logger = logging.getLogger(__name__)


@dr_mcp_tool(tags={"monitoring", "deployment", "list"})
async def list_deployments(
    search: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    ユーザーがアクセス可能なデプロイメント一覧を取得

    Args:
        search: デプロイメント名の検索キーワード（部分一致、オプション）
        limit: 取得する最大件数（デフォルト: 20）

    Returns:
        デプロイメント一覧（マークダウン形式）
        - デプロイメントID、名前（ラベル）、ステータス
        - 作成日時
    """
    try:
        deployments = Deployment.list()

        # 検索キーワードでフィルタ
        if search:
            search_lower = search.lower()
            deployments = [
                d
                for d in deployments
                if search_lower in (d.label or "").lower()
                or search_lower in (d.description or "").lower()
            ]

        # 件数制限
        deployments = deployments[:limit]

        if not deployments:
            if search:
                return f'"{search}" に一致するデプロイメントが見つかりませんでした。'
            return "アクセス可能なデプロイメントがありません。"

        report = f"""## デプロイメント一覧

取得件数: {len(deployments)}件{f' (検索: "{search}")' if search else ''}

| # | デプロイメント名 | デプロイメントID | ステータス |
|---|-----------------|----------------|----------|
"""

        for i, d in enumerate(deployments, 1):
            report += (
                f"| {i} | {d.label or 'N/A'} "
                f"| `{d.id}` | {d.status or 'N/A'} |\n"
            )

        report += (
            "\n**ヒント**: デプロイメントIDを使って "
            "`get_deployment_overview` や `diagnose_deployment_issues` "
            "で詳細を確認できます。"
        )

        return report

    except Exception as e:
        return f"デプロイメント一覧の取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "deployment", "search"})
async def find_deployment_by_name(
    deployment_name: str,
) -> str:
    """
    デプロイメント名（ラベル）からデプロイメントIDを検索・解決する。
    ユーザーがデプロイメント名で指定した場合、このツールでIDに変換してから
    他の監視ツールを実行する。

    Args:
        deployment_name: デプロイメント名（部分一致で検索、例: "deploy-agent"）

    Returns:
        マッチしたデプロイメント情報（JSON形式）
        - 完全一致がある場合はそのデプロイメントのID
        - 部分一致が複数ある場合は候補一覧
    """
    try:
        deployments = Deployment.list()

        name_lower = deployment_name.lower()

        # 完全一致を優先検索
        exact_matches = [
            d for d in deployments if (d.label or "").lower() == name_lower
        ]

        if len(exact_matches) == 1:
            d = exact_matches[0]
            result = {
                "match_type": "exact",
                "deployment_id": d.id,
                "label": d.label,
                "status": d.status,
                "description": d.description,
            }
            return json.dumps(result, ensure_ascii=False, indent=2)

        # 部分一致検索
        partial_matches = [
            d for d in deployments if name_lower in (d.label or "").lower()
        ]

        if len(partial_matches) == 0:
            return (
                f'"{deployment_name}" に一致するデプロイメントが見つかりません。\n'
                "`list_deployments` で利用可能なデプロイメント一覧を確認してください。"
            )

        if len(partial_matches) == 1:
            d = partial_matches[0]
            result = {
                "match_type": "partial",
                "deployment_id": d.id,
                "label": d.label,
                "status": d.status,
                "description": d.description,
            }
            return json.dumps(result, ensure_ascii=False, indent=2)

        # 複数候補がある場合
        candidates = []
        for d in partial_matches[:10]:
            candidates.append(
                {
                    "deployment_id": d.id,
                    "label": d.label,
                    "status": d.status,
                }
            )

        result_multi = {
            "match_type": "multiple",
            "message": f'"{deployment_name}" に複数のデプロイメントがマッチしました。どれを使いますか？',
            "candidates": candidates,
        }
        return json.dumps(result_multi, ensure_ascii=False, indent=2)

    except Exception as e:
        return f"デプロイメント検索中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "deployment", "overview"})
async def get_deployment_overview(deployment_id: str) -> str:
    """
    デプロイメントの概要情報を取得

    Args:
        deployment_id: デプロイメントID（例: "698587ff226830d448db7b99"）

    Returns:
        デプロイメント詳細情報（JSON形式）
        - デプロイメントID、ラベル、ステータス
        - モデルタイプ、ターゲットタイプ
        - 予測環境、作成日時
    """
    try:
        deployment = Deployment.get(deployment_id=deployment_id)

        overview = {
            "deployment_id": deployment.id,
            "label": deployment.label,
            "status": deployment.status,
            "description": deployment.description,
            "model_type": deployment.model.get("type") if deployment.model else None,
            "target_type": (
                deployment.model.get("target_type") if deployment.model else None
            ),
            "prediction_environment": {
                "id": (
                    deployment.default_prediction_server.get("id")
                    if deployment.default_prediction_server
                    else None
                ),
                "url": (
                    deployment.default_prediction_server.get("url")
                    if deployment.default_prediction_server
                    else None
                ),
            },
            "created_at": str(deployment.created_at),
            "importance": deployment.importance,
        }

        return json.dumps(overview, ensure_ascii=False, indent=2)

    except Exception as e:
        return f"デプロイメント情報の取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "service", "health"})
async def get_service_health(
    deployment_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> str:
    """
    サービスヘルス統計を取得

    Args:
        deployment_id: デプロイメントID
        start_time: 開始時刻（ISO形式、例: "2026-02-06T00:00:00Z"）
        end_time: 終了時刻（ISO形式、例: "2026-02-07T00:00:00Z"）

    Returns:
        サービス統計情報（マークダウン形式）
        - 総リクエスト数、エラー数、成功率
        - 平均レスポンス時間、P95レスポンス時間
        - データエラー、システムエラーの詳細
    """
    try:
        deployment = Deployment.get(deployment_id=deployment_id)

        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        else:
            end_dt = datetime.now(timezone.utc)

        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        else:
            start_dt = end_dt - timedelta(hours=24)

        service_stats = deployment.get_service_stats(start=start_dt, end=end_dt)

        total_requests = service_stats.metrics.get("totalRequests", 0)
        total_errors = service_stats.metrics.get("totalErrors", 0)
        success_rate = (
            ((total_requests - total_errors) / total_requests * 100)
            if total_requests > 0
            else 0
        )

        health_report = f"""## サービスヘルス: {deployment.label}

### 期間
- **開始**: {start_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}
- **終了**: {end_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}

### リクエスト統計
- **総リクエスト数**: {total_requests:,}
- **エラー数**: {total_errors:,}
- **成功率**: {success_rate:.2f}%

### パフォーマンス
- **平均レスポンス時間**: {service_stats.metrics.get('avgResponseTime', 'N/A')}ms
- **P95レスポンス時間**: {service_stats.metrics.get('p95ResponseTime', 'N/A')}ms
- **最大レスポンス時間**: {service_stats.metrics.get('maxResponseTime', 'N/A')}ms

### エラー内訳
- **データエラー**: {service_stats.metrics.get('dataErrors', 0)}
- **システムエラー**: {service_stats.metrics.get('systemErrors', 0)}"""

        return health_report

    except Exception as e:
        return f"サービスヘルス取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "trace", "agentic"})
async def get_recent_traces(
    deployment_id: str,
    limit: int = 10,
    filter_status: Optional[str] = None,
) -> str:
    """
    最近のトレース情報を取得（エージェントワークフロー用）

    Args:
        deployment_id: デプロイメントID
        limit: 取得するトレース数（1-100、デフォルト: 10）
        filter_status: ステータスフィルタ（"success", "error", "all"）

    Returns:
        トレース情報（マークダウン形式）
        - Trace ID、タイムスタンプ、ステータス
        - 実行時間、ツール使用状況
        - エラーがある場合はエラー詳細
    """
    try:
        deployment = Deployment.get(deployment_id=deployment_id)

        # Data Exploration APIからトレースデータを取得
        # deployment.get_predictions() や関連APIを利用
        trace_summary = f"""## 最近のトレース: {deployment.label}

取得件数: {limit}件
フィルタ: {filter_status or '全て'}

### トレース一覧

| Trace ID | タイムスタンプ | ステータス | 実行時間 | ツール使用 |
|----------|--------------|----------|---------|-----------|
"""

        # 実際のトレースデータ取得を試行
        try:
            # DataRobot Data Exploration API経由でトレース取得
            import datarobot as dr

            params = {
                "deploymentId": deployment_id,
                "limit": limit,
            }
            if filter_status and filter_status != "all":
                params["status"] = filter_status

            response = dr.Client().get(  # type: ignore[attr-defined]
                f"deployments/{deployment_id}/dataExploration/traces/",
                params=params,
            )

            if response.status_code == 200:
                traces = response.json().get("data", [])
                if traces:
                    for trace in traces:
                        trace_id = trace.get("traceId", "N/A")
                        timestamp = trace.get("timestamp", "N/A")
                        status = trace.get("status", "N/A")
                        duration = trace.get("duration", "N/A")
                        tools = trace.get("tools", "N/A")
                        # Trace IDは先頭16文字+...で表示
                        display_id = (
                            f"{trace_id[:16]}..."
                            if len(str(trace_id)) > 16
                            else trace_id
                        )
                        trace_summary += (
                            f"| {display_id} | {timestamp} "
                            f"| {status} | {duration}ms | {tools} |\n"
                        )
                else:
                    trace_summary += (
                        "| - | - | - | - | データがありません |\n"
                    )
            else:
                trace_summary += (
                    f"| - | - | - | - | API応答: {response.status_code} |\n"
                )
        except Exception as api_err:
            trace_summary += (
                f"| - | - | - | - | データ取得エラー: {str(api_err)[:50]} |\n"
            )

        trace_summary += """
**注意**: 詳細なトレース情報を確認するには、`search_trace_by_id` ツールを使用してください。"""

        return trace_summary

    except Exception as e:
        return f"トレース取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "trace", "detail"})
async def search_trace_by_id(
    deployment_id: str,
    trace_id: str,
) -> str:
    """
    特定のTrace IDの詳細情報を取得

    Args:
        deployment_id: デプロイメントID
        trace_id: トレースID（例: "e8aee2e2ee9bc3f655105bd96769b7ff"）

    Returns:
        トレース詳細（マークダウン形式）
        - Span情報（親子関係、実行順序）
        - 各SpanのInput/Output
        - エラー情報（存在する場合）
        - パフォーマンスメトリクス
    """
    try:
        deployment = Deployment.get(deployment_id=deployment_id)

        trace_detail = f"""## トレース詳細

**Trace ID**: `{trace_id}`
**Deployment**: {deployment.label}
"""

        # OpenTelemetry APIを使用してトレース詳細を取得
        try:
            import datarobot as dr

            response = dr.Client().get(  # type: ignore[attr-defined]
                f"deployments/{deployment_id}/dataExploration/traces/{trace_id}/",
            )

            if response.status_code == 200:
                trace_data = response.json()

                spans = trace_data.get("spans", [])
                if spans:
                    trace_detail += "\n### Span階層構造\n\n```\n"
                    for span in spans:
                        name = span.get("name", "unknown")
                        duration = span.get("duration", "N/A")
                        depth = span.get("depth", 0)
                        indent = "  " * depth
                        prefix = "├─ " if depth > 0 else ""
                        trace_detail += (
                            f"{indent}{prefix}{name} [{duration}ms]\n"
                        )
                    trace_detail += "```\n"

                    trace_detail += "\n### 詳細メトリクス\n\n"
                    trace_detail += (
                        "| Span | 実行時間 | ステータス |\n"
                        "|------|---------|----------|\n"
                    )
                    for span in spans:
                        name = span.get("name", "unknown")
                        duration = span.get("duration", "N/A")
                        status = span.get("status", "N/A")
                        trace_detail += (
                            f"| {name} | {duration}ms | {status} |\n"
                        )

                    # エラー情報
                    error_spans = [s for s in spans if s.get("status") == "error"]
                    if error_spans:
                        trace_detail += "\n### エラー情報\n\n"
                        for err_span in error_spans:
                            trace_detail += (
                                f"- **{err_span.get('name')}**: "
                                f"{err_span.get('error_message', 'エラー詳細なし')}\n"
                            )
                else:
                    trace_detail += (
                        "\nSpan情報が見つかりませんでした。\n"
                    )
            else:
                trace_detail += (
                    f"\nトレースデータの取得に失敗しました "
                    f"(ステータス: {response.status_code})\n"
                )
        except Exception as api_err:
            trace_detail += (
                f"\nトレース詳細APIの呼び出しに失敗しました: {str(api_err)}\n"
                "\nDataRobot UIのトレース詳細画面で確認してください。"
            )

        return trace_detail

    except Exception as e:
        return f"トレース詳細取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "error", "analysis"})
async def analyze_errors(
    deployment_id: str,
    time_range_hours: int = 24,
    error_type: Optional[str] = None,
) -> str:
    """
    エラーを分析し、パターンや頻度を特定

    Args:
        deployment_id: デプロイメントID
        time_range_hours: 分析対象の時間範囲（時間単位、デフォルト: 24）
        error_type: エラータイプフィルタ（"data_error", "system_error", "all"）

    Returns:
        エラー分析レポート（マークダウン形式）
        - エラー総数、エラー率
        - エラータイプ別の内訳
        - 頻出エラーメッセージ
        - 推奨される対応アクション
    """
    try:
        deployment = Deployment.get(deployment_id=deployment_id)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_range_hours)

        service_stats = deployment.get_service_stats(start=start_time, end=end_time)

        total_requests = service_stats.metrics.get("totalRequests", 0)
        total_errors = service_stats.metrics.get("totalErrors", 0)
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

        data_errors = service_stats.metrics.get("dataErrors", 0)
        system_errors = service_stats.metrics.get("systemErrors", 0)

        data_error_pct = (
            (data_errors / total_errors * 100) if total_errors > 0 else 0
        )
        system_error_pct = (
            (system_errors / total_errors * 100) if total_errors > 0 else 0
        )

        error_report = f"""## エラー分析: {deployment.label}

### 分析期間
- **過去 {time_range_hours} 時間**
- {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')} UTC

### サマリー
- **総リクエスト数**: {total_requests:,}
- **総エラー数**: {total_errors:,}
- **エラー率**: {error_rate:.2f}%

### エラー内訳
- **データエラー**: {data_errors} ({data_error_pct:.1f}%)
- **システムエラー**: {system_errors} ({system_error_pct:.1f}%)

### 推奨アクション
"""

        if error_rate > 10:
            error_report += (
                "**高エラー率検出** - 緊急対応が必要です\n"
                "- システムログを確認してください\n"
                "- 最近のデプロイメント変更を確認してください\n"
            )
        elif error_rate > 5:
            error_report += (
                "**中程度のエラー率** - 監視を強化してください\n"
                "- エラーパターンを詳細分析してください\n"
            )
        elif total_errors > 0:
            error_report += (
                "**低エラー率** - 正常範囲内ですが注視してください\n"
                "- エラー内容を定期的に確認してください\n"
            )
        else:
            error_report += "**エラーなし** - 正常に稼働しています\n"

        return error_report

    except Exception as e:
        return f"エラー分析中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "performance", "metrics"})
async def get_performance_metrics(
    deployment_id: str,
    metric_type: str = "latency",
    time_range_hours: int = 24,
) -> str:
    """
    パフォーマンスメトリクスを取得

    Args:
        deployment_id: デプロイメントID
        metric_type: メトリクスタイプ（"latency", "throughput", "cost", "all"）
        time_range_hours: 分析対象の時間範囲（時間単位、デフォルト: 24）

    Returns:
        パフォーマンスメトリクス（マークダウン形式）
        - レイテンシ統計（平均、P50、P95、P99）
        - スループット（リクエスト/時）
        - コスト情報（LLMトークン使用量など）
        - トレンド分析
    """
    try:
        deployment = Deployment.get(deployment_id=deployment_id)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_range_hours)

        service_stats = deployment.get_service_stats(start=start_time, end=end_time)

        total_requests = service_stats.metrics.get("totalRequests", 0)
        avg_latency = service_stats.metrics.get("avgResponseTime", 0)

        metrics_report = f"""## パフォーマンスメトリクス: {deployment.label}

### 分析期間
- **過去 {time_range_hours} 時間**

### レイテンシ統計
- **平均**: {service_stats.metrics.get('avgResponseTime', 'N/A')}ms
- **中央値 (P50)**: {service_stats.metrics.get('p50ResponseTime', 'N/A')}ms
- **P95**: {service_stats.metrics.get('p95ResponseTime', 'N/A')}ms
- **P99**: {service_stats.metrics.get('p99ResponseTime', 'N/A')}ms
- **最大**: {service_stats.metrics.get('maxResponseTime', 'N/A')}ms

### スループット
- **総リクエスト数**: {total_requests:,}
- **平均リクエスト/時**: {total_requests / time_range_hours:.1f}

### 推奨事項
"""

        if isinstance(avg_latency, (int, float)) and avg_latency > 10000:
            metrics_report += (
                "**高レイテンシ検出** - 最適化が必要です\n"
                "- LLMモデルの変更を検討してください\n"
                "- ツール呼び出しの並列化を検討してください\n"
            )
        elif isinstance(avg_latency, (int, float)) and avg_latency > 5000:
            metrics_report += "**レイテンシがやや高い** - 監視を継続してください\n"
        else:
            metrics_report += "**良好なパフォーマンス**\n"

        return metrics_report

    except Exception as e:
        return f"パフォーマンスメトリクス取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "diagnosis", "automatic"})
async def diagnose_deployment_issues(
    deployment_id: str,
) -> str:
    """
    デプロイメントの問題を自動診断

    Args:
        deployment_id: デプロイメントID

    Returns:
        診断レポート（マークダウン形式）
        - 検出された問題
        - 問題の重要度
        - 推奨される対処方法
        - ヘルスチェックスコア
    """
    try:
        deployment = Deployment.get(deployment_id=deployment_id)

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        service_stats = deployment.get_service_stats(start=start_time, end=end_time)

        issues = []
        health_score = 100

        # 1. エラー率チェック
        total_requests = service_stats.metrics.get("totalRequests", 0)
        total_errors = service_stats.metrics.get("totalErrors", 0)
        error_rate = (
            (total_errors / total_requests * 100) if total_requests > 0 else 0
        )

        if error_rate > 10:
            issues.append(
                {
                    "severity": "critical",
                    "issue": f"高エラー率（{error_rate:.1f}%）",
                    "impact": "多数のユーザーリクエストが失敗しています",
                    "action": "エラーログを確認し、原因を特定してください",
                }
            )
            health_score -= 30
        elif error_rate > 5:
            issues.append(
                {
                    "severity": "high",
                    "issue": f"中程度のエラー率（{error_rate:.1f}%）",
                    "impact": "一部のユーザーリクエストが失敗しています",
                    "action": "エラーパターンを分析してください",
                }
            )
            health_score -= 15

        # 2. レイテンシチェック
        avg_latency = service_stats.metrics.get("avgResponseTime", 0)
        if isinstance(avg_latency, (int, float)):
            if avg_latency > 10000:
                issues.append(
                    {
                        "severity": "high",
                        "issue": f"高レイテンシ（平均 {avg_latency}ms）",
                        "impact": "ユーザー体験が著しく悪化しています",
                        "action": "パフォーマンス最適化が必要です",
                    }
                )
                health_score -= 20
            elif avg_latency > 5000:
                issues.append(
                    {
                        "severity": "medium",
                        "issue": f"やや高いレイテンシ（平均 {avg_latency}ms）",
                        "impact": "ユーザー体験が低下している可能性があります",
                        "action": "パフォーマンスを監視してください",
                    }
                )
                health_score -= 10

        # 3. デプロイメントステータスチェック
        if deployment.status != "active":
            issues.append(
                {
                    "severity": "critical",
                    "issue": f"デプロイメントステータスが異常（{deployment.status}）",
                    "impact": "デプロイメントが正常に動作していません",
                    "action": "デプロイメントの設定を確認してください",
                }
            )
            health_score -= 40

        # ヘルススコアの評価
        health_score = max(health_score, 0)
        if health_score >= 90:
            health_status = "優良"
        elif health_score >= 70:
            health_status = "注意"
        elif health_score >= 50:
            health_status = "警告"
        else:
            health_status = "緊急"

        severity_emoji = {
            "critical": "[CRITICAL]",
            "high": "[HIGH]",
            "medium": "[MEDIUM]",
            "low": "[LOW]",
        }

        report = f"""## デプロイメント診断レポート

**デプロイメント**: {deployment.label}
**デプロイメントID**: {deployment_id}
**診断時刻**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC

### ヘルススコア
**{health_score}/100** - {health_status}

"""

        if issues:
            report += "### 検出された問題\n\n"
            for i, issue in enumerate(issues, 1):
                report += f"""{severity_emoji[issue['severity']]} **問題 {i}: {issue['issue']}**
- **重要度**: {issue['severity'].upper()}
- **影響**: {issue['impact']}
- **推奨アクション**: {issue['action']}

"""
        else:
            report += (
                "### 問題は検出されませんでした\n\n"
                "デプロイメントは正常に動作しています。"
                "継続的な監視を推奨します。\n"
            )

        report += f"""
### サマリー統計（過去24時間）
- **総リクエスト数**: {total_requests:,}
- **エラー数**: {total_errors}
- **エラー率**: {error_rate:.2f}%
- **平均レスポンス時間**: {avg_latency}ms

### 次のステップ
"""

        if health_score < 70:
            report += (
                "1. 緊急: 検出された問題に対処してください\n"
                "2. `analyze_errors` ツールでエラーの詳細を確認\n"
                "3. `get_recent_traces` ツールで最近の実行状況を確認\n"
            )
        else:
            report += (
                "1. 継続的な監視を続けてください\n"
                "2. 定期的に `diagnose_deployment_issues` を実行して健全性を確認\n"
            )

        return report

    except Exception as e:
        return f"デプロイメント診断中にエラーが発生しました: {str(e)}"

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from datarobot.models import Deployment
from datarobot_genai.drmcp import dr_mcp_tool

logger = logging.getLogger(__name__)


def _truncate_to_hour(dt: datetime) -> datetime:
    """DataRobot APIが要求する「時間のトップ」に切り捨て（分・秒を0に）"""
    return dt.replace(minute=0, second=0, microsecond=0)


def _fmt_dt(dt_val: object) -> str:
    """datetime値またはISO文字列を表示用文字列にフォーマット"""
    if dt_val is None:
        return "N/A"
    if isinstance(dt_val, datetime):
        return dt_val.strftime("%Y-%m-%d %H:%M")
    # 文字列の場合はISO形式をパース試行
    try:
        parsed = datetime.fromisoformat(str(dt_val).replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(dt_val)[:16]


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
        - 作成日時、最終予測日時
    """
    try:
        import datarobot as dr

        # REST APIを直接呼んで createdAt, predictionUsage を含む完全なデータを取得
        client = dr.Client()  # type: ignore[attr-defined]
        response = client.get("deployments/", params={"limit": limit})

        if response.status_code != 200:
            # フォールバック: SDK経由
            return await _list_deployments_fallback(search, limit)

        data = response.json().get("data", [])

        # 検索キーワードでフィルタ
        if search:
            search_lower = search.lower()
            data = [
                d for d in data
                if search_lower in (d.get("label") or "").lower()
                or search_lower in (d.get("description") or "").lower()
            ]

        if not data:
            if search:
                return f'"{search}" に一致するデプロイメントが見つかりませんでした。'
            return "アクセス可能なデプロイメントがありません。"

        report = f"""## デプロイメント一覧

取得件数: {len(data)}件{f' (検索: "{search}")' if search else ''}

| # | デプロイメント名 | デプロイメントID | ステータス | 作成日 | 最終予測日時 |
|---|-----------------|----------------|----------|-------|------------|
"""

        for i, d in enumerate(data, 1):
            label = d.get("label") or "N/A"
            dep_id = d.get("id") or "N/A"
            status = d.get("status") or "N/A"
            created = _fmt_dt(d.get("createdAt"))
            # predictionUsage.lastPredictionTimestamp から最終予測日時を取得
            pred_usage = d.get("predictionUsage") or {}
            last_pred = _fmt_dt(pred_usage.get("lastPredictionTimestamp"))
            report += (
                f"| {i} | {label} "
                f"| `{dep_id}` | {status} "
                f"| {created} | {last_pred} |\n"
            )

        report += (
            "\n**ヒント**: デプロイメントIDを使って "
            "`get_deployment_overview` や `diagnose_deployment_issues` "
            "で詳細を確認できます。"
        )

        return report

    except Exception as e:
        return f"デプロイメント一覧の取得中にエラーが発生しました: {str(e)}"


async def _list_deployments_fallback(
    search: Optional[str] = None,
    limit: int = 20,
) -> str:
    """SDK経由のフォールバック（REST APIが使えない場合）"""
    deployments = Deployment.list()

    if search:
        search_lower = search.lower()
        deployments = [
            d for d in deployments
            if search_lower in (d.label or "").lower()
            or search_lower in (d.description or "").lower()
        ]

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
        - 総リクエスト数、総予測数
        - 実行時間、レスポンス時間
        - サーバーエラー率、ユーザーエラー率
        - リクエスト負荷（中央値・ピーク）
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

        # DataRobot APIは時間のトップ（XX:00:00）を要求する
        start_dt = _truncate_to_hour(start_dt)
        end_dt = _truncate_to_hour(end_dt)

        service_stats = deployment.get_service_stats(start_time=start_dt, end_time=end_dt)
        m = service_stats.metrics

        total_requests = m.get("totalRequests") or 0
        total_predictions = m.get("totalPredictions") or 0
        server_error_rate = m.get("serverErrorRate")
        user_error_rate = m.get("userErrorRate")
        execution_time = m.get("executionTime")
        response_time = m.get("responseTime")
        slow_requests = m.get("slowRequests")
        num_consumers = m.get("numConsumers")
        median_load = m.get("medianLoad")
        peak_load = m.get("peakLoad")
        cache_hit_ratio = m.get("cacheHitRatio")

        # エラー率から推定エラー数を計算
        server_errors = (
            int(total_requests * server_error_rate)
            if server_error_rate is not None and total_requests > 0
            else 0
        )
        user_errors = (
            int(total_requests * user_error_rate)
            if user_error_rate is not None and total_requests > 0
            else 0
        )
        total_errors = server_errors + user_errors
        success_rate = (
            ((1 - (server_error_rate or 0) - (user_error_rate or 0)) * 100)
            if total_requests > 0
            else 0
        )

        def fmt_ms(val: object) -> str:
            if val is None:
                return "N/A"
            return f"{val:,.1f}ms" if isinstance(val, (int, float)) else str(val)

        def fmt_rate(val: object) -> str:
            if val is None:
                return "N/A"
            return (
                f"{val * 100:.2f}%" if isinstance(val, (int, float)) else str(val)
            )

        def fmt_load(val: object) -> str:
            if val is None:
                return "N/A"
            return (
                f"{val:.1f} req/min" if isinstance(val, (int, float)) else str(val)
            )

        health_report = f"""## サービスヘルス: {deployment.label}

### 期間
- **開始**: {start_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}
- **終了**: {end_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}

### リクエスト統計
- **総リクエスト数**: {total_requests:,}
- **総予測数**: {total_predictions:,}
- **推定エラー数**: {total_errors:,}
- **成功率**: {success_rate:.2f}%
- **ユニークユーザー数**: {num_consumers if num_consumers is not None else 'N/A'}

### パフォーマンス
- **実行時間**: {fmt_ms(execution_time)}
- **レスポンス時間**: {fmt_ms(response_time)}
- **低速リクエスト数**: {slow_requests if slow_requests is not None else 'N/A'}
- **キャッシュヒット率**: {fmt_rate(cache_hit_ratio)}

### エラー内訳
- **サーバーエラー率**: {fmt_rate(server_error_rate)}
- **ユーザーエラー率**: {fmt_rate(user_error_rate)}

### リクエスト負荷
- **中央値**: {fmt_load(median_load)}
- **ピーク**: {fmt_load(peak_load)}"""

        return health_report

    except Exception as e:
        return f"サービスヘルス取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "trace", "agentic"})
async def get_recent_traces(
    deployment_id: str,
    limit: int = 10,
    time_range_hours: int = 24,
) -> str:
    """
    最近の予測データ（トレース）を取得（PredictionDataExport API経由）

    Args:
        deployment_id: デプロイメントID
        limit: 表示する最大件数（デフォルト: 10）
        time_range_hours: 取得対象の時間範囲（時間単位、デフォルト: 24）

    Returns:
        予測データ一覧（マークダウン形式）
        - アソシエーションID、タイムスタンプ
        - 予測結果、レスポンス時間
    """
    try:
        deployment = Deployment.get(deployment_id=deployment_id)

        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(hours=time_range_hours)

        trace_summary = f"""## 最近の予測データ: {deployment.label}

### 期間
- {start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%Y-%m-%d %H:%M')} UTC

"""

        try:
            from datarobot.models.deployment import PredictionDataExport

            prediction_export = PredictionDataExport.create(
                deployment_id=deployment_id,
                start=start_dt,
                end=end_dt,
            )
            datasets = prediction_export.fetch_data()

            if datasets:
                df = datasets[0].get_as_dataframe()
                total_rows = len(df)
                display_df = df.head(limit)

                trace_summary += f"取得件数: {total_rows}件（表示: {len(display_df)}件）\n\n"

                # カラム情報を表示
                columns = list(df.columns)
                trace_summary += f"### データカラム\n`{', '.join(columns[:20])}`"
                if len(columns) > 20:
                    trace_summary += f" ...他{len(columns) - 20}列"
                trace_summary += "\n\n"

                # データを表形式で表示（主要カラムを選択）
                display_cols = []
                for col_candidate in [
                    "association_id",
                    "ASSOCIATION_ID",
                    "timestamp",
                    "TIMESTAMP",
                    "prediction",
                    "predicted_value",
                    "class_label",
                    "response_time",
                ]:
                    if col_candidate in columns:
                        display_cols.append(col_candidate)

                if not display_cols:
                    display_cols = columns[:5]

                trace_summary += "### データ一覧\n\n"
                trace_summary += "| " + " | ".join(display_cols) + " |\n"
                trace_summary += "|" + "|".join(["---"] * len(display_cols)) + "|\n"

                for _, row in display_df.iterrows():
                    vals = []
                    for col in display_cols:
                        val = str(row.get(col, "N/A"))
                        if len(val) > 40:
                            val = val[:37] + "..."
                        vals.append(val)
                    trace_summary += "| " + " | ".join(vals) + " |\n"
            else:
                trace_summary += "予測データが見つかりませんでした。\n"
                trace_summary += (
                    "\n**注意**: 予測データを取得するには、"
                    "デプロイメントで予測データの保存が有効になっている必要があります。"
                )

        except ImportError:
            trace_summary += (
                "PredictionDataExport が利用できません。\n"
                "datarobot パッケージのバージョンを確認してください。"
            )
        except Exception as api_err:
            error_msg = str(api_err)
            if "prediction data storage" in error_msg.lower() or "not enabled" in error_msg.lower():
                trace_summary += (
                    "予測データの保存が有効になっていません。\n\n"
                    "**対処方法**: DataRobot UIでデプロイメント設定 → "
                    "「予測データの保存」を有効にしてください。"
                )
            else:
                trace_summary += f"予測データの取得に失敗しました: {error_msg}\n"

        return trace_summary

    except Exception as e:
        return f"予測データ取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "trace", "detail"})
async def search_trace_by_id(
    deployment_id: str,
    association_id: str,
) -> str:
    """
    特定のアソシエーションIDの予測データ詳細を取得

    Args:
        deployment_id: デプロイメントID
        association_id: アソシエーションID（予測リクエストの識別子）

    Returns:
        予測データ詳細（マークダウン形式）
        - 予測入力データ
        - 予測結果
        - メトリクス情報
    """
    try:
        deployment = Deployment.get(deployment_id=deployment_id)

        detail = f"""## 予測データ詳細

**アソシエーションID**: `{association_id}`
**デプロイメント**: {deployment.label}

"""

        try:
            from datarobot.models.deployment import PredictionDataExport

            # 直近7日間のデータからアソシエーションIDで検索
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=7)

            prediction_export = PredictionDataExport.create(
                deployment_id=deployment_id,
                start=start_dt,
                end=end_dt,
            )
            datasets = prediction_export.fetch_data()

            if datasets:
                df = datasets[0].get_as_dataframe()

                # アソシエーションIDカラムを検索
                assoc_col = None
                for col_candidate in ["association_id", "ASSOCIATION_ID", "associationId"]:
                    if col_candidate in df.columns:
                        assoc_col = col_candidate
                        break

                matched = None
                if assoc_col:
                    matched = df[df[assoc_col].astype(str) == str(association_id)]

                if matched is not None and len(matched) > 0:
                    row = matched.iloc[0]
                    detail += "### 予測データ\n\n"
                    for col in df.columns:
                        val = str(row[col])
                        if len(val) > 200:
                            val = val[:197] + "..."
                        detail += f"- **{col}**: {val}\n"
                else:
                    detail += (
                        f"アソシエーションID `{association_id}` に一致する"
                        "データが見つかりませんでした。\n\n"
                        "**ヒント**: \n"
                        "- IDが正しいか確認してください\n"
                        "- `get_recent_traces` で最近のデータを確認してください\n"
                        "- 7日以上前のデータは検索できません\n"
                    )
            else:
                detail += "予測データが見つかりませんでした。\n"

        except ImportError:
            detail += (
                "PredictionDataExport が利用できません。\n"
                "datarobot パッケージのバージョンを確認してください。"
            )
        except Exception as api_err:
            detail += f"予測データの取得に失敗しました: {str(api_err)}\n"

        return detail

    except Exception as e:
        return f"予測データ詳細取得中にエラーが発生しました: {str(e)}"


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

        end_time = _truncate_to_hour(datetime.now(timezone.utc))
        start_time = _truncate_to_hour(end_time - timedelta(hours=time_range_hours))

        service_stats = deployment.get_service_stats(start_time=start_time, end_time=end_time)
        m = service_stats.metrics

        total_requests = m.get("totalRequests") or 0
        server_error_rate = m.get("serverErrorRate") or 0
        user_error_rate = m.get("userErrorRate") or 0
        total_error_rate = server_error_rate + user_error_rate
        error_rate_pct = total_error_rate * 100

        server_errors = (
            int(total_requests * server_error_rate) if total_requests > 0 else 0
        )
        user_errors = (
            int(total_requests * user_error_rate) if total_requests > 0 else 0
        )
        total_errors = server_errors + user_errors

        error_report = f"""## エラー分析: {deployment.label}

### 分析期間
- **過去 {time_range_hours} 時間**
- {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')} UTC

### サマリー
- **総リクエスト数**: {total_requests:,}
- **推定エラー数**: {total_errors:,}
- **エラー率**: {error_rate_pct:.2f}%

### エラー内訳
- **サーバーエラー率**: {server_error_rate * 100:.2f}% (推定 {server_errors} 件)
- **ユーザーエラー率**: {user_error_rate * 100:.2f}% (推定 {user_errors} 件)

### 推奨アクション
"""

        if error_rate_pct > 10:
            error_report += (
                "**高エラー率検出** - 緊急対応が必要です\n"
                "- システムログを確認してください\n"
                "- 最近のデプロイメント変更を確認してください\n"
            )
        elif error_rate_pct > 5:
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

        end_time = _truncate_to_hour(datetime.now(timezone.utc))
        start_time = _truncate_to_hour(end_time - timedelta(hours=time_range_hours))

        service_stats = deployment.get_service_stats(start_time=start_time, end_time=end_time)
        m = service_stats.metrics

        total_requests = m.get("totalRequests") or 0
        total_predictions = m.get("totalPredictions") or 0
        execution_time = m.get("executionTime")
        response_time = m.get("responseTime")
        slow_requests = m.get("slowRequests")
        median_load = m.get("medianLoad")
        peak_load = m.get("peakLoad")
        cache_hit_ratio = m.get("cacheHitRatio")

        def fmt_ms(val: object) -> str:
            if val is None:
                return "N/A"
            return f"{val:,.1f}ms" if isinstance(val, (int, float)) else str(val)

        def fmt_load(val: object) -> str:
            if val is None:
                return "N/A"
            return (
                f"{val:.1f} req/min" if isinstance(val, (int, float)) else str(val)
            )

        metrics_report = f"""## パフォーマンスメトリクス: {deployment.label}

### 分析期間
- **過去 {time_range_hours} 時間**

### レイテンシ統計
- **実行時間**: {fmt_ms(execution_time)}
- **レスポンス時間**: {fmt_ms(response_time)}
- **低速リクエスト数**: {slow_requests if slow_requests is not None else 'N/A'}

### スループット
- **総リクエスト数**: {total_requests:,}
- **総予測数**: {total_predictions:,}
- **平均リクエスト/時**: {total_requests / time_range_hours:.1f}
- **中央値負荷**: {fmt_load(median_load)}
- **ピーク負荷**: {fmt_load(peak_load)}
- **キャッシュヒット率**: {f"{cache_hit_ratio * 100:.1f}%" if cache_hit_ratio is not None else "N/A"}

### 推奨事項
"""

        if isinstance(response_time, (int, float)) and response_time > 10000:
            metrics_report += (
                "**高レイテンシ検出** - 最適化が必要です\n"
                "- LLMモデルの変更を検討してください\n"
                "- ツール呼び出しの並列化を検討してください\n"
            )
        elif isinstance(response_time, (int, float)) and response_time > 5000:
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

        end_time = _truncate_to_hour(datetime.now(timezone.utc))
        start_time = _truncate_to_hour(end_time - timedelta(hours=24))
        service_stats = deployment.get_service_stats(start_time=start_time, end_time=end_time)
        m = service_stats.metrics

        issues = []
        health_score = 100

        # 1. エラー率チェック
        total_requests = m.get("totalRequests") or 0
        server_error_rate = m.get("serverErrorRate") or 0
        user_error_rate = m.get("userErrorRate") or 0
        total_error_rate = server_error_rate + user_error_rate
        error_rate = total_error_rate * 100
        total_errors = (
            int(total_requests * total_error_rate) if total_requests > 0 else 0
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
        avg_latency = m.get("responseTime") or 0
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


@dr_mcp_tool(tags={"monitoring", "metrics", "custom", "llm"})
async def get_custom_metrics(
    deployment_id: str,
    time_range_hours: int = 24,
) -> str:
    """
    デプロイメントのカスタムメトリクス（LLMコスト、トークン使用量等）を取得

    Args:
        deployment_id: デプロイメントID
        time_range_hours: 取得対象の時間範囲（時間単位、デフォルト: 24）

    Returns:
        カスタムメトリクス一覧（マークダウン形式）
        - メトリクス名、値、タイムスタンプ
        - LLMトークン使用量、コスト情報（設定されている場合）
    """
    try:
        deployment = Deployment.get(deployment_id=deployment_id)

        report = f"""## カスタムメトリクス: {deployment.label}

### 期間: 過去 {time_range_hours} 時間

"""

        try:
            import datarobot as dr

            # カスタムメトリクス一覧を取得
            response = dr.Client().get(  # type: ignore[attr-defined]
                f"deployments/{deployment_id}/customMetrics/",
            )

            if response.status_code == 200:
                metrics_data = response.json().get("data", [])

                if not metrics_data:
                    report += (
                        "カスタムメトリクスが設定されていません。\n\n"
                        "**ヒント**: DataRobot UIでカスタムメトリクスを追加すると、"
                        "LLMコスト、トークン使用量等を監視できます。"
                    )
                    return report

                report += f"登録済みメトリクス数: {len(metrics_data)}\n\n"

                # 各メトリクスの値を取得
                end_dt = datetime.now(timezone.utc)
                start_dt = end_dt - timedelta(hours=time_range_hours)

                report += (
                    "| メトリクス名 | タイプ | 最新値 | 説明 |\n"
                    "|-------------|-------|-------|------|\n"
                )

                for metric in metrics_data:
                    metric_id = metric.get("id", "")
                    metric_name = metric.get("name", "N/A")
                    metric_type = metric.get("type", "N/A")
                    description = metric.get("description", "")
                    if len(description) > 50:
                        description = description[:47] + "..."

                    # メトリクス値を取得
                    latest_value = "N/A"
                    try:
                        val_response = dr.Client().get(  # type: ignore[attr-defined]
                            f"deployments/{deployment_id}/customMetrics/{metric_id}/values/",
                            params={
                                "start": start_dt.isoformat(),
                                "end": end_dt.isoformat(),
                            },
                        )
                        if val_response.status_code == 200:
                            val_data = val_response.json()
                            buckets = val_data.get("buckets", [])
                            if buckets:
                                # 最新バケットの値を取得
                                last_bucket = buckets[-1]
                                val = last_bucket.get("value")
                                if val is not None:
                                    if isinstance(val, float):
                                        latest_value = f"{val:.4f}"
                                    else:
                                        latest_value = str(val)
                    except Exception:
                        pass

                    report += (
                        f"| {metric_name} | {metric_type} "
                        f"| {latest_value} | {description} |\n"
                    )

                report += (
                    "\n**注意**: カスタムメトリクスの詳細な時系列データは "
                    "DataRobot UIのカスタムメトリクスタブで確認できます。"
                )
            else:
                report += (
                    f"カスタムメトリクスの取得に失敗しました "
                    f"(ステータス: {response.status_code})\n"
                )

        except Exception as api_err:
            report += f"カスタムメトリクスAPIの呼び出しに失敗しました: {str(api_err)}\n"

        return report

    except Exception as e:
        return f"カスタムメトリクス取得中にエラーが発生しました: {str(e)}"

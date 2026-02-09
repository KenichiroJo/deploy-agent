import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from datarobot_genai.drmcp import dr_mcp_tool

logger = logging.getLogger(__name__)

# 開発時: メモリ内リスト（本番ではDB/Redisに置き換え）
USER_ACTIVITY_LOG: list[dict[str, object]] = []


def log_user_activity(
    deployment_id: str,
    user_id: str,
    tool_name: str,
    query: str,
    error: bool = False,
    error_message: Optional[str] = None,
) -> None:
    """
    ユーザーアクティビティをログに記録

    注: 実運用ではデータベースやRedisなどの永続ストレージを使用
    """
    global USER_ACTIVITY_LOG

    USER_ACTIVITY_LOG.append(
        {
            "timestamp": datetime.now(timezone.utc),
            "deployment_id": deployment_id,
            "user_id": user_id,
            "tool_name": tool_name,
            "query": query,
            "error": error,
            "error_message": error_message,
        }
    )

    # メモリ管理: 古いログを削除（過去7日以上）
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
    USER_ACTIVITY_LOG = [
        log
        for log in USER_ACTIVITY_LOG
        if isinstance(log["timestamp"], datetime) and log["timestamp"] > cutoff_time
    ]


@dr_mcp_tool(tags={"monitoring", "user", "usage"})
async def get_user_usage_stats(
    deployment_id: str,
    user_id: Optional[str] = None,
    time_range_hours: int = 24,
) -> str:
    """
    ユーザー単位の利用統計を取得

    Args:
        deployment_id: デプロイメントID
        user_id: ユーザーID（指定しない場合は全ユーザー）
        time_range_hours: 分析対象の時間範囲（時間単位、デフォルト: 24）

    Returns:
        ユーザー利用統計（マークダウン形式）
        - ユーザー別のリクエスト数
        - ユーザー別のエラー率
        - よく使われるツール
        - アクティブ時間帯
    """
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_range_hours)

        filtered_logs = [
            log
            for log in USER_ACTIVITY_LOG
            if log["deployment_id"] == deployment_id
            and isinstance(log["timestamp"], datetime)
            and start_time <= log["timestamp"] <= end_time
            and (user_id is None or log["user_id"] == user_id)
        ]

        if not filtered_logs:
            return f"過去{time_range_hours}時間の利用データがありません。"

        # ユーザー別に集計
        user_stats: dict[str, dict[str, object]] = {}
        for log in filtered_logs:
            uid = str(log["user_id"])
            if uid not in user_stats:
                user_stats[uid] = {
                    "total_requests": 0,
                    "errors": 0,
                    "tools_used": {},
                }

            user_stats[uid]["total_requests"] = (  # type: ignore[assignment]
                int(user_stats[uid]["total_requests"]) + 1  # type: ignore[arg-type]
            )
            if log.get("error"):
                user_stats[uid]["errors"] = (  # type: ignore[assignment]
                    int(user_stats[uid]["errors"]) + 1  # type: ignore[arg-type]
                )

            tool = str(log.get("tool_name", "unknown"))
            tools_used = user_stats[uid]["tools_used"]
            if isinstance(tools_used, dict):
                tools_used[tool] = tools_used.get(tool, 0) + 1  # type: ignore[assignment, operator]

        report = f"""## ユーザー利用統計

**デプロイメントID**: {deployment_id}
**分析期間**: 過去 {time_range_hours} 時間

### ユーザー別サマリー
"""

        for uid, stats in user_stats.items():
            total = int(stats["total_requests"])  # type: ignore[arg-type]
            errors = int(stats["errors"])  # type: ignore[arg-type]
            error_rate = (errors / total * 100) if total > 0 else 0
            tools_used = stats["tools_used"]
            most_used_tool = "なし"
            if isinstance(tools_used, dict) and tools_used:
                most_used_tool = max(tools_used.items(), key=lambda x: x[1])[0]  # type: ignore[arg-type]

            report += f"""
#### ユーザー: {uid}
- **総リクエスト数**: {total}
- **エラー数**: {errors}
- **エラー率**: {error_rate:.1f}%
- **最も使用されたツール**: {most_used_tool}
"""

        return report

    except Exception as e:
        return f"ユーザー利用統計の取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "user", "summary"})
async def get_all_users_summary(
    deployment_id: str,
    time_range_hours: int = 24,
) -> str:
    """
    全ユーザーの利用サマリーを取得

    Args:
        deployment_id: デプロイメントID
        time_range_hours: 分析対象の時間範囲（時間単位、デフォルト: 24）

    Returns:
        全ユーザーの利用サマリー（マークダウン形式）
        - アクティブユーザー数
        - 総リクエスト数
        - 平均エラー率
        - 人気のある機能
    """
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_range_hours)

        filtered_logs = [
            log
            for log in USER_ACTIVITY_LOG
            if log["deployment_id"] == deployment_id
            and isinstance(log["timestamp"], datetime)
            and start_time <= log["timestamp"] <= end_time
        ]

        if not filtered_logs:
            return f"過去{time_range_hours}時間の利用データがありません。"

        unique_users = set(str(log["user_id"]) for log in filtered_logs)
        total_requests = len(filtered_logs)
        total_errors = sum(1 for log in filtered_logs if log.get("error"))

        # ツール別使用回数
        tool_usage: dict[str, int] = {}
        for log in filtered_logs:
            tool = str(log.get("tool_name", "unknown"))
            tool_usage[tool] = tool_usage.get(tool, 0) + 1

        top_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:3]

        error_rate = (
            (total_errors / total_requests * 100) if total_requests > 0 else 0
        )

        summary = f"""## 全ユーザー利用サマリー

**デプロイメントID**: {deployment_id}
**分析期間**: 過去 {time_range_hours} 時間

### 全体統計
- **アクティブユーザー数**: {len(unique_users)}
- **総リクエスト数**: {total_requests}
- **総エラー数**: {total_errors}
- **全体エラー率**: {error_rate:.1f}%

### 人気機能 TOP3
"""

        for i, (tool, count) in enumerate(top_tools, 1):
            percentage = (count / total_requests * 100) if total_requests > 0 else 0
            summary += f"{i}. **{tool}**: {count}回 ({percentage:.1f}%)\n"

        if not top_tools:
            summary += "データがありません\n"

        return summary

    except Exception as e:
        return f"全ユーザーサマリーの取得中にエラーが発生しました: {str(e)}"

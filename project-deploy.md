# DataRobot デプロイメント監視エージェント - プロジェクト設計書

## 📋 プロジェクト概要

### 目的
DataRobot社内メンバーがAIエージェントのデプロイメント監視を効率化するため、UI上で複数の画面を行き来する代わりに、**チャット形式で自然言語で監視情報を確認・分析できるエージェント**を構築する。

### 背景
- **課題**: エージェントデプロイメントの監視情報（トレース、サービスヘルス、エラーログなど）を確認するには、DataRobot UIで複数のタブを開いて深掘りする必要があり、時間がかかる
- **解決策**: 自然言語で「最近のエラーは？」「パフォーマンスが悪化している原因は？」などと質問すると、監視データを自動取得・分析して回答するエージェント
- **ユーザー**: DataRobot社員（エージェント開発者、MLOpsエンジニア、サポートチーム）
- **開発環境**: DataRobot codespace

### 技術的実現可能性
✅ **実現可能** - 以下のDataRobot API/SDKが利用可能：
1. **OpenTelemetryベースのトレース取得**: Trace ID、Span情報、Input/Output、実行時間
2. **Deployment API**: デプロイメント詳細、ステータス、環境情報
3. **Service Stats API**: エラー率、レイテンシ、リクエスト数
4. **Data Exploration API**: 予測データ、トレース履歴、評価結果
5. **Custom Metrics API**: LLMコスト、トークン使用量、カスタム指標

---

## 🏗️ アーキテクチャ

### 全体構成

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│            自然言語での監視クエリ入力                            │
│     例: "deployment 698587ff の最新エラーを教えて"              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓ (plain text)
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend Server                      │
│                  (/chat エンドポイント)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓ invoke({"input": "..."})
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph Agent                            │
│        (DeploymentMonitoringAgent - ReAct Pattern)          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  System Prompt: デプロイメント監視エキスパート         │   │
│  │  - トレース分析                                       │   │
│  │  - パフォーマンス診断                                 │   │
│  │  - エラー調査                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                     │
│                         ↓ (tool selection)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              MCP Tools (自動統合)                      │   │
│  │  - get_deployment_overview                           │   │
│  │  - get_recent_traces                                 │   │
│  │  - get_service_health                                │   │
│  │  - analyze_errors                                    │   │
│  │  - get_performance_metrics                           │   │
│  │  - search_trace_by_id                                │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              DataRobot REST API / Python SDK                 │
│  - Deployment API                                            │
│  - OpenTelemetry Trace API                                   │
│  - Service Stats API                                         │
│  - Data Exploration API                                      │
└─────────────────────────────────────────────────────────────┘
```

### デザインパターン: ReAct + DataRobot API Integration

**重要**: このプロジェクトは**LangGraphのReActパターン**を採用します。

```python
# エージェント構造 (copilot-instructions.md準拠)
create_react_agent(
    llm=self.llm(preferred_model="datarobot/azure/gpt-4o"),
    tools=self.mcp_tools,  # DataRobot監視ツールを自動ロード
    prompt=make_system_prompt(system_prompt_content)
)
```

---

## 🛠️ 技術スタック

### Backend & Orchestration
- **Framework**: LangGraph (`langgraph.graph.StateGraph`)
- **State**: `MessagesState` (標準のMessagesStateを使用)
- **API Server**: FastAPI
- **AI Integration**: `datarobot_genai` (LLM Gateway統合)
- **Tools**: Model Context Protocol (MCP) Server
- **DataRobot SDK**: `datarobot` Python Client (>= 3.11.0)

### Frontend
- **Framework**: React
- **Language**: TypeScript
- **Input**: Plain text only
- **Output**: Markdown + JSON parsing (トレース情報、グラフ、テーブル)

### Infrastructure
- **IaC**: Pulumi
- **Deployment**: DataRobot Custom Model Application
- **Environment**: DataRobot codespace

### 開発ツール
- **Python**: 3.10+
- **Package Manager**: uv
- **Task Runner**: Taskfile
- **Version Control**: Git

---

## 📁 ディレクトリ構造

```
datarobot-agent-application-main/
├── agent/                                    # エージェント本体
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── config.py                        # 設定管理
│   │   └── monitoring_agent.py              # 🆕 監視エージェント実装
│   ├── pyproject.toml
│   └── tests/
│
├── mcp_server/                               # MCPサーバー (ツール定義)
│   ├── app/
│   │   ├── tools/
│   │   │   ├── user_tools.py
│   │   │   ├── deployment_monitoring_tools.py  # 🆕 監視ツール群
│   │   │   ├── user_monitoring_tools.py        # 🆕 ユーザー監視ツール
│   │   │   └── error_resolution_tools.py       # 🆕 エラー対処ツール
│   │   ├── prompts/
│   │   ├── resources/
│   │   └── main.py
│   ├── pyproject.toml
│   └── .env                                  # 環境変数設定
│
├── fastapi_server/                           # FastAPI Backend
│   ├── app/
│   │   ├── routers/
│   │   └── main.py
│   └── pyproject.toml
│
├── frontend_web/                             # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   └── MonitoringDashboard.tsx      # 🆕 監視ダッシュボード
│   │   └── App.tsx
│   └── package.json
│
└── copilot-instructions.md                   # 開発ガイドライン
```

---

## 🎯 実装する機能

### Phase 1: 基本監視機能 (MVP)

#### 1.1 DataRobot監視ツール群
**ファイル**: `mcp_server/app/tools/deployment_monitoring_tools.py`

```python
from datarobot.models import Deployment
from datarobot_genai.drmcp import dr_mcp_tool
import json
from datetime import datetime, timedelta
from typing import Optional

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
            "model_type": deployment.model.get("type"),
            "target_type": deployment.model.get("target_type"),
            "prediction_environment": {
                "id": deployment.default_prediction_server.get("id"),
                "url": deployment.default_prediction_server.get("url")
            },
            "created_at": str(deployment.created_at),
            "importance": deployment.importance
        }
        
        return json.dumps(overview, ensure_ascii=False, indent=2)
    
    except Exception as e:
        return f"デプロイメント情報の取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "service", "health"})
async def get_service_health(
    deployment_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
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
        
        # 時刻指定がない場合は過去24時間
        if not end_time:
            end_time = datetime.utcnow()
        else:
            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        else:
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        
        # サービス統計取得
        service_stats = deployment.get_service_stats(
            start=start_time,
            end=end_time
        )
        
        # マークダウン形式で整形
        total_requests = service_stats.metrics.get('totalRequests', 0)
        total_errors = service_stats.metrics.get('totalErrors', 0)
        success_rate = ((total_requests - total_errors) / total_requests * 100) if total_requests > 0 else 0
        
        health_report = f"""
## サービスヘルス: {deployment.label}

### 期間
- **開始**: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}
- **終了**: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}

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
- **システムエラー**: {service_stats.metrics.get('systemErrors', 0)}
        """
        
        return health_report.strip()
    
    except Exception as e:
        return f"サービスヘルス取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "trace", "agentic"})
async def get_recent_traces(
    deployment_id: str,
    limit: int = 10,
    filter_status: Optional[str] = None
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
        
        # Data Explorationからトレースデータを取得
        # 注: 実際のAPI仕様に応じて実装を調整
        # ここでは擬似的な実装例を示す
        
        trace_summary = f"""
## 最近のトレース: {deployment.label}

取得件数: {limit}件
フィルタ: {filter_status or '全て'}

### トレース一覧

| Trace ID | タイムスタンプ | ステータス | 実行時間 | ツール使用 |
|----------|--------------|----------|---------|-----------|
"""
        
        # 注: 実際の実装では Data Exploration API を使用してトレースを取得
        # 以下は例示
        trace_summary += "| e8aee2e2ee9bc3f65... | 2026-02-06 15:32:33 | Success | 37192ms | LangGraph.workflow, mcp.request.tools/list |\n"
        trace_summary += "| e8aee2e2ee9bc3f65... | 2026-02-06 15:20:31 | Success | 35392ms | POST, mcp.request.initialize |\n"
        
        trace_summary += f"""
**注意**: 詳細なトレース情報を確認するには、`search_trace_by_id` ツールを使用してください。
"""
        
        return trace_summary.strip()
    
    except Exception as e:
        return f"トレース取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "trace", "detail"})
async def search_trace_by_id(
    deployment_id: str,
    trace_id: str
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
        
        # OpenTelemetry APIを使用してトレース詳細を取得
        # 注: 実際のAPI実装に応じて調整が必要
        
        trace_detail = f"""
## トレース詳細

**Trace ID**: `{trace_id}`
**Deployment**: {deployment.label}

### Span階層構造

```
Root Span: LangGraph.workflow [35392.37ms]
  ├─ agent.task [6815.86ms]
  ├─ POST [350.24ms]
  ├─ mcp.request.initialize [0.52ms]
  ├─ POST [60.65ms]
  ├─ POST [134.81ms]
  └─ mcp.request.tools/list [0.15ms]
```

### 詳細メトリクス

| Span | 実行時間 | ステータス | Input/Output |
|------|---------|----------|-------------|
| LangGraph.workflow | 35392.37ms | Success | [詳細表示] |
| agent.task | 6815.86ms | Success | [詳細表示] |

**注意**: 実際のInput/Output詳細はDataRobot UIのトレース詳細画面で確認できます。
"""
        
        return trace_detail.strip()
    
    except Exception as e:
        return f"トレース詳細取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "error", "analysis"})
async def analyze_errors(
    deployment_id: str,
    time_range_hours: int = 24,
    error_type: Optional[str] = None
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
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        # サービス統計からエラー情報を取得
        service_stats = deployment.get_service_stats(
            start=start_time,
            end=end_time
        )
        
        total_requests = service_stats.metrics.get('totalRequests', 0)
        total_errors = service_stats.metrics.get('totalErrors', 0)
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        error_report = f"""
## エラー分析: {deployment.label}

### 分析期間
- **過去 {time_range_hours} 時間**
- {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')} UTC

### サマリー
- **総リクエスト数**: {total_requests:,}
- **総エラー数**: {total_errors:,}
- **エラー率**: {error_rate:.2f}%

### エラー内訳
- **データエラー**: {service_stats.metrics.get('dataErrors', 0)} ({service_stats.metrics.get('dataErrors', 0) / total_errors * 100 if total_errors > 0 else 0:.1f}%)
- **システムエラー**: {service_stats.metrics.get('systemErrors', 0)} ({service_stats.metrics.get('systemErrors', 0) / total_errors * 100 if total_errors > 0 else 0:.1f}%)

### 推奨アクション
"""
        
        # エラー率に基づいた推奨アクション
        if error_rate > 10:
            error_report += "⚠️ **高エラー率検出** - 緊急対応が必要です\n"
            error_report += "- システムログを確認してください\n"
            error_report += "- 最近のデプロイメント変更を確認してください\n"
        elif error_rate > 5:
            error_report += "⚡ **中程度のエラー率** - 監視を強化してください\n"
            error_report += "- エラーパターンを詳細分析してください\n"
        else:
            error_report += "✅ **正常範囲内** - 継続的な監視を続けてください\n"
        
        return error_report.strip()
    
    except Exception as e:
        return f"エラー分析中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "performance", "metrics"})
async def get_performance_metrics(
    deployment_id: str,
    metric_type: str = "latency",
    time_range_hours: int = 24
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
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        service_stats = deployment.get_service_stats(
            start=start_time,
            end=end_time
        )
        
        metrics_report = f"""
## パフォーマンスメトリクス: {deployment.label}

### 分析期間
- **過去 {time_range_hours} 時間**

### レイテンシ統計
- **平均**: {service_stats.metrics.get('avgResponseTime', 'N/A')}ms
- **中央値 (P50)**: {service_stats.metrics.get('p50ResponseTime', 'N/A')}ms
- **P95**: {service_stats.metrics.get('p95ResponseTime', 'N/A')}ms
- **P99**: {service_stats.metrics.get('p99ResponseTime', 'N/A')}ms
- **最大**: {service_stats.metrics.get('maxResponseTime', 'N/A')}ms

### スループット
- **総リクエスト数**: {service_stats.metrics.get('totalRequests', 0):,}
- **平均リクエスト/時**: {service_stats.metrics.get('totalRequests', 0) / time_range_hours:.1f}

### 推奨事項
"""
        
        # パフォーマンスに基づいた推奨
        avg_latency = service_stats.metrics.get('avgResponseTime', 0)
        if avg_latency > 10000:  # 10秒以上
            metrics_report += "⚠️ **高レイテンシ検出** - 最適化が必要です\n"
            metrics_report += "- LLMモデルの変更を検討してください\n"
            metrics_report += "- ツール呼び出しの並列化を検討してください\n"
        elif avg_latency > 5000:  # 5秒以上
            metrics_report += "⚡ **レイテンシがやや高い** - 監視を継続してください\n"
        else:
            metrics_report += "✅ **良好なパフォーマンス**\n"
        
        return metrics_report.strip()
    
    except Exception as e:
        return f"パフォーマンスメトリクス取得中にエラーが発生しました: {str(e)}"
```

#### 1.2 監視エージェント実装
**ファイル**: `agent/agent/monitoring_agent.py`

```python
from typing import Any
from datarobot_genai.core.agents import make_system_prompt
from datarobot_genai.langgraph.agent import LangGraphAgent
from langchain_litellm.chat_models import ChatLiteLLM
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import create_react_agent
from agent.config import Config

config = Config()

class DeploymentMonitoringAgent(LangGraphAgent):
    """
    DataRobotデプロイメント監視に特化したエージェント。
    トレース分析、パフォーマンス診断、エラー調査を自然言語で実行。
    """

    @property
    def workflow(self) -> StateGraph[MessagesState]:
        """シンプルなReActフロー (copilot-instructions.md準拠)"""
        langgraph_workflow = StateGraph[
            MessagesState, None, MessagesState, MessagesState
        ](MessagesState)
        
        langgraph_workflow.add_node("monitoring_node", self.monitoring_agent)
        langgraph_workflow.add_edge(START, "monitoring_node")
        langgraph_workflow.add_edge("monitoring_node", END)
        
        return langgraph_workflow

    @property
    def monitoring_agent(self) -> Any:
        """監視エージェントノード"""
        return create_react_agent(
            self.llm(preferred_model="datarobot/azure/gpt-4o"),
            tools=self.mcp_tools,  # 監視ツールを自動含む
            prompt=make_system_prompt(
                "あなたはDataRobotのデプロイメント監視エキスパートです。\n"
                "\n"
                "## 役割\n"
                "AIエージェントのデプロイメントを監視し、トレース分析、パフォーマンス診断、\n"
                "エラー調査を実施します。社内メンバーが迅速に問題を特定・解決できるよう支援します。\n"
                "\n"
                "## 利用可能なツール\n"
                "\n"
                "### 基本情報\n"
                "- **get_deployment_overview**: デプロイメントの概要情報（ID、ステータス、環境）\n"
                "\n"
                "### サービスヘルス\n"
                "- **get_service_health**: リクエスト数、エラー率、レスポンス時間\n"
                "- **analyze_errors**: エラーパターン分析、頻出エラー特定\n"
                "- **diagnose_deployment_issues**: デプロイメントの問題を自動診断\n"
                "\n"
                "### トレース分析\n"
                "- **get_recent_traces**: 最近のトレース一覧（時系列）\n"
                "- **search_trace_by_id**: 特定トレースの詳細（Span階層、Input/Output）\n"
                "\n"
                "### パフォーマンス\n"
                "- **get_performance_metrics**: レイテンシ、スループット、コスト分析\n"
                "\n"
                "### ユーザー監視（マルチユーザー対応）\n"
                "- **get_user_usage_stats**: ユーザー単位の利用統計\n"
                "- **get_all_users_summary**: 全ユーザーの利用サマリー\n"
                "\n"
                "### エラー対処支援\n"
                "- **suggest_error_resolution**: エラーメッセージに基づく対処方法の提案\n"
                "- **get_error_resolution_history**: 過去のエラーと対処履歴\n"
                "\n"
                "## ユーザークエリの理解\n"
                "\n"
                "### クエリパターンとツール選択\n"
                "1. **「デプロイメント情報を教えて」** → `get_deployment_overview`\n"
                "2. **「最近のエラーは？」** → `analyze_errors`\n"
                "3. **「パフォーマンスが悪化している」** → `get_performance_metrics` → `get_service_health`\n"
                "4. **「trace ID XXX の詳細」** → `search_trace_by_id`\n"
                "5. **「今日のトレース一覧」** → `get_recent_traces`\n"
                "6. **「ヘルスチェック」** → `get_service_health` → `analyze_errors`\n"
                "7. **「ユーザーごとの利用状況」** → `get_user_usage_stats`\n"
                "8. **「全体の利用状況」** → `get_all_users_summary`\n"
                "9. **「このエラーの対処方法は？」** → `suggest_error_resolution`\n"
                "10. **「過去のエラー履歴」** → `get_error_resolution_history`\n"
                "11. **「問題がないか診断して」** → `diagnose_deployment_issues`\n"
                "\n"
                "### デプロイメントIDの扱い\n"
                "- ユーザーが明示的にIDを指定した場合: そのまま使用\n"
                "- 「このデプロイメント」「現在のデプロイメント」: コンテキストから推定\n"
                "- IDが不明な場合: ユーザーに確認を求める\n"
                "\n"
                "## 回答フォーマット\n"
                "\n"
                "### 1. 概要回答（簡潔に）\n"
                "質問に対する直接的な答えを1-2文で提示\n"
                "\n"
                "### 2. 詳細データ（構造化）\n"
                "ツールから取得したデータをそのまま表示（マークダウンテーブル、リストなど）\n"
                "\n"
                "### 3. 推奨アクション（必要に応じて）\n"
                "- 問題が検出された場合: 具体的な対応手順\n"
                "- 正常な場合: 継続的な監視ポイント\n"
                "\n"
                "### 4. 関連情報（オプション）\n"
                "さらに深掘りできる質問例や、関連ツールの提案\n"
                "\n"
                "## 重要な原則\n"
                "\n"
                "1. **データドリブン**: 必ずツールを使って実際のデータを取得してから回答\n"
                "2. **簡潔性**: 冗長な説明は避け、要点を明確に\n"
                "3. **実用性**: 社内メンバーが即座にアクションできる情報を提供\n"
                "4. **文脈理解**: 過去の会話を考慮し、適切なツールを選択\n"
                "5. **エラーハンドリング**: ツール実行エラー時は、代替手段を提案\n"
                "\n"
                "## 例\n"
                "\n"
                "### 良い回答例\n"
                "```\n"
                "ユーザー: deployment 698587ff の最新エラーを教えて\n"
                "\n"
                "エージェント:\n"
                "過去24時間で12件のエラーが発生しています（エラー率: 2.3%）。\n"
                "\n"
                "[analyze_errors の結果を表示]\n"
                "\n"
                "**推奨アクション**:\n"
                "データエラーが多いため、入力データの形式を確認してください。\n"
                "```\n"
                "\n"
                "### 避けるべき回答例\n"
                "```\n"
                "エージェント:\n"
                "デプロイメントのエラーを確認するには、まず... [長い説明]\n"
                "一般的にエラーには... [一般論]\n"
                "```\n"
                "\n"
                "## トラブルシューティングフロー\n"
                "\n"
                "問題報告があった場合の推奨調査順序:\n"
                "1. `get_deployment_overview` - 基本状態確認\n"
                "2. `get_service_health` - 全体的なヘルスチェック\n"
                "3. `analyze_errors` - エラーパターン特定\n"
                "4. `get_recent_traces` - 最近の実行状況確認\n"
                "5. `search_trace_by_id` - 特定エラーの詳細調査\n"
                "6. `get_performance_metrics` - パフォーマンスボトルネック特定"
            ),
            name="Deployment Monitoring Agent",
        )

    def llm(
        self,
        preferred_model: str | None = None,
        auto_model_override: bool = True,
    ) -> ChatLiteLLM:
        """LLM設定 (テンプレートから継承)"""
        api_base = self.litellm_api_base(config.llm_deployment_id)
        model = preferred_model or config.llm_default_model
        
        if auto_model_override and not config.use_datarobot_llm_gateway:
            model = config.llm_default_model
        
        if self.verbose:
            print(f"Using model: {model}")
        
        return ChatLiteLLM(
            model=model,
            api_base=api_base,
            api_key=self.api_key,
            timeout=self.timeout,
            streaming=True,
            max_retries=3,
        )
```

### Phase 2: マルチユーザー監視とエラー対処提案

#### 2.1 マルチユーザー対応の設計

**課題**: 複数のユーザー（開発者、MLOpsエンジニア、サポートチーム）が同一エージェントを利用する場合、ユーザー単位での利用状況を追跡する必要がある。

**解決策**:
1. **ユーザー識別**: DataRobot APIキーまたはセッション情報からユーザーを識別
2. **利用統計の記録**: ユーザーごとのリクエスト数、エラー率、使用ツールを記録
3. **集計レポート**: ユーザー別、チーム別、時間別の利用統計を提供

#### 2.2 マルチユーザー監視ツール

**ファイル**: `mcp_server/app/tools/user_monitoring_tools.py`

```python
from datarobot_genai.drmcp import dr_mcp_tool
from datetime import datetime, timedelta
from typing import Optional, List
import json

# 注: 実運用ではデータベースやRedisなどの永続ストレージを使用
# ここでは簡略化のためメモリ内に保存
USER_ACTIVITY_LOG = []

@dr_mcp_tool(tags={"monitoring", "user", "usage"})
async def get_user_usage_stats(
    deployment_id: str,
    user_id: Optional[str] = None,
    time_range_hours: int = 24
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
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        # ユーザーアクティビティログをフィルタリング
        filtered_logs = [
            log for log in USER_ACTIVITY_LOG
            if log['deployment_id'] == deployment_id
            and start_time <= log['timestamp'] <= end_time
            and (user_id is None or log['user_id'] == user_id)
        ]
        
        if not filtered_logs:
            return f"過去{time_range_hours}時間の利用データがありません。"
        
        # ユーザー別に集計
        user_stats = {}
        for log in filtered_logs:
            uid = log['user_id']
            if uid not in user_stats:
                user_stats[uid] = {
                    'total_requests': 0,
                    'errors': 0,
                    'tools_used': {},
                    'queries': []
                }
            
            user_stats[uid]['total_requests'] += 1
            if log.get('error'):
                user_stats[uid]['errors'] += 1
            
            tool = log.get('tool_name', 'unknown')
            user_stats[uid]['tools_used'][tool] = user_stats[uid]['tools_used'].get(tool, 0) + 1
            user_stats[uid]['queries'].append(log.get('query', ''))
        
        # レポート生成
        report = f"""
## ユーザー利用統計

**デプロイメントID**: {deployment_id}
**分析期間**: 過去 {time_range_hours} 時間

### ユーザー別サマリー
"""
        
        for uid, stats in user_stats.items():
            error_rate = (stats['errors'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
            most_used_tool = max(stats['tools_used'].items(), key=lambda x: x[1])[0] if stats['tools_used'] else 'なし'
            
            report += f"""
#### ユーザー: {uid}
- **総リクエスト数**: {stats['total_requests']}
- **エラー数**: {stats['errors']}
- **エラー率**: {error_rate:.1f}%
- **最も使用されたツール**: {most_used_tool}
"""
        
        return report.strip()
    
    except Exception as e:
        return f"ユーザー利用統計の取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"monitoring", "user", "summary"})
async def get_all_users_summary(
    deployment_id: str,
    time_range_hours: int = 24
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
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        filtered_logs = [
            log for log in USER_ACTIVITY_LOG
            if log['deployment_id'] == deployment_id
            and start_time <= log['timestamp'] <= end_time
        ]
        
        if not filtered_logs:
            return f"過去{time_range_hours}時間の利用データがありません。"
        
        # 全体統計を計算
        unique_users = set(log['user_id'] for log in filtered_logs)
        total_requests = len(filtered_logs)
        total_errors = sum(1 for log in filtered_logs if log.get('error'))
        
        # ツール別使用回数
        tool_usage = {}
        for log in filtered_logs:
            tool = log.get('tool_name', 'unknown')
            tool_usage[tool] = tool_usage.get(tool, 0) + 1
        
        # 人気ツールTOP3
        top_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:3]
        
        summary = f"""
## 全ユーザー利用サマリー

**デプロイメントID**: {deployment_id}
**分析期間**: 過去 {time_range_hours} 時間

### 全体統計
- **アクティブユーザー数**: {len(unique_users)}
- **総リクエスト数**: {total_requests}
- **総エラー数**: {total_errors}
- **全体エラー率**: {(total_errors / total_requests * 100) if total_requests > 0 else 0:.1f}%

### 人気機能 TOP3
"""
        
        for i, (tool, count) in enumerate(top_tools, 1):
            percentage = (count / total_requests * 100) if total_requests > 0 else 0
            summary += f"{i}. **{tool}**: {count}回 ({percentage:.1f}%)\n"
        
        summary += f"""
### ユーザー分布
- **1-5リクエスト**: {len([u for u in unique_users if sum(1 for log in filtered_logs if log['user_id'] == u) <= 5])} ユーザー
- **6-20リクエスト**: {len([u for u in unique_users if 6 <= sum(1 for log in filtered_logs if log['user_id'] == u) <= 20])} ユーザー
- **21+リクエスト**: {len([u for u in unique_users if sum(1 for log in filtered_logs if log['user_id'] == u) > 20])} ユーザー
"""
        
        return summary.strip()
    
    except Exception as e:
        return f"全ユーザーサマリーの取得中にエラーが発生しました: {str(e)}"


# アクティビティログ記録用のヘルパー関数
def log_user_activity(
    deployment_id: str,
    user_id: str,
    tool_name: str,
    query: str,
    error: bool = False,
    error_message: Optional[str] = None
):
    """
    ユーザーアクティビティをログに記録
    
    注: 実運用ではデータベースやRedisなどの永続ストレージを使用
    """
    USER_ACTIVITY_LOG.append({
        'timestamp': datetime.utcnow(),
        'deployment_id': deployment_id,
        'user_id': user_id,
        'tool_name': tool_name,
        'query': query,
        'error': error,
        'error_message': error_message
    })
    
    # メモリ管理: 古いログを削除（過去7日以上）
    cutoff_time = datetime.utcnow() - timedelta(days=7)
    global USER_ACTIVITY_LOG
    USER_ACTIVITY_LOG = [
        log for log in USER_ACTIVITY_LOG
        if log['timestamp'] > cutoff_time
    ]
```

#### 2.3 エラー対処提案ツール

**ファイル**: `mcp_server/app/tools/error_resolution_tools.py`

```python
from datarobot_genai.drmcp import dr_mcp_tool
from typing import Optional, Dict, List
import json

# エラータイプ別の対処方法データベース
ERROR_RESOLUTION_DB = {
    "deployment_not_found": {
        "error_pattern": "deployment.*not found|404",
        "title": "デプロイメントが見つかりません",
        "severity": "high",
        "steps": [
            "1. デプロイメントIDが正しいか確認してください",
            "2. DataRobot UIでデプロイメントが存在するか確認",
            "3. デプロイメントが削除されていないか確認",
            "4. アクセス権限があるか確認（共有設定を確認）"
        ],
        "prevention": [
            "デプロイメントIDをコピー＆ペーストで使用する",
            "削除されたデプロイメントのIDを保存しない"
        ]
    },
    "api_authentication_error": {
        "error_pattern": "authentication|unauthorized|401|403",
        "title": "API認証エラー",
        "severity": "critical",
        "steps": [
            "1. 環境変数 DATAROBOT_API_TOKEN が正しく設定されているか確認",
            "2. API keyの有効期限を確認（DataRobot UI > API keys and tools）",
            "3. API keyが有効化されているか確認",
            "4. API keyに適切な権限があるか確認"
        ],
        "prevention": [
            "API keyの定期的なローテーション",
            "環境変数の定期確認"
        ]
    },
    "rate_limit_exceeded": {
        "error_pattern": "rate limit|too many requests|429",
        "title": "レート制限超過",
        "severity": "medium",
        "steps": [
            "1. リクエスト頻度を下げる（バックオフ戦略を実装）",
            "2. 必要な場合はDataRobot管理者にレート制限の引き上げを依頼",
            "3. キャッシュを活用してAPI呼び出しを削減",
            "4. バッチ処理で複数のリクエストをまとめる"
        ],
        "prevention": [
            "リクエストのスロットリング実装",
            "結果のキャッシング"
        ]
    },
    "data_format_error": {
        "error_pattern": "invalid data|format error|schema",
        "title": "データフォーマットエラー",
        "severity": "medium",
        "steps": [
            "1. 入力データのスキーマを確認",
            "2. 必須フィールドがすべて含まれているか確認",
            "3. データ型が正しいか確認（文字列、数値、日付など）",
            "4. サンプルデータでテストしてみる"
        ],
        "prevention": [
            "入力データのバリデーション実装",
            "スキーマ定義の文書化"
        ]
    },
    "timeout_error": {
        "error_pattern": "timeout|timed out",
        "title": "タイムアウトエラー",
        "severity": "high",
        "steps": [
            "1. ネットワーク接続を確認",
            "2. タイムアウト設定を延長（大量データ処理の場合）",
            "3. データサイズを削減してリクエストを分割",
            "4. DataRobotサービスのステータスを確認"
        ],
        "prevention": [
            "適切なタイムアウト設定",
            "大量データの分割処理"
        ]
    },
    "trace_not_available": {
        "error_pattern": "trace.*not available|no trace data",
        "title": "トレースデータが利用できません",
        "severity": "low",
        "steps": [
            "1. デプロイメント設定でトレース機能が有効か確認",
            "2. Data Explorationで予測データ保存が有効か確認",
            "3. トレースIDが正しいか確認",
            "4. トレースデータの保持期間内か確認"
        ],
        "prevention": [
            "デプロイメント作成時にトレース機能を有効化",
            "定期的なデータアーカイブ"
        ]
    }
}


@dr_mcp_tool(tags={"error", "resolution", "suggestion"})
async def suggest_error_resolution(
    error_message: str,
    deployment_id: Optional[str] = None,
    context: Optional[str] = None
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
        import re
        
        # エラーメッセージを小文字に変換してパターンマッチング
        error_lower = error_message.lower()
        
        # マッチするエラータイプを検索
        matched_error = None
        for error_type, error_info in ERROR_RESOLUTION_DB.items():
            pattern = error_info['error_pattern']
            if re.search(pattern, error_lower):
                matched_error = error_info
                break
        
        if not matched_error:
            # 既知のエラーパターンにマッチしない場合
            return f"""
## エラー対処提案

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
- 実行したリクエストの詳細

詳細については、DataRobot docsを参照してください:
https://docs.datarobot.com/en/docs/get-started/troubleshooting/general-help.html
"""
        
        # マッチしたエラーの対処方法を生成
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }
        
        resolution = f"""
## エラー対処提案

{severity_emoji.get(matched_error['severity'], '⚪')} **{matched_error['title']}**

**エラーメッセージ**: {error_message}
**重要度**: {matched_error['severity'].upper()}

### 対処手順

"""
        
        for step in matched_error['steps']:
            resolution += f"{step}\n"
        
        resolution += f"""
### 予防策

"""
        
        for prevention in matched_error['prevention']:
            resolution += f"- {prevention}\n"
        
        # コンテキスト情報を追加
        if deployment_id:
            resolution += f"""
### コンテキスト情報
- **デプロイメントID**: {deployment_id}
"""
        
        if context:
            resolution += f"- **追加情報**: {context}\n"
        
        resolution += """
### 関連リソース
- [DataRobot トラブルシューティングガイド](https://docs.datarobot.com/en/docs/get-started/troubleshooting/general-help.html)
- [DataRobot API リファレンス](https://docs.datarobot.com/en/docs/api/reference/index.html)
- [DataRobot サポート](https://support.datarobot.com)
"""
        
        return resolution.strip()
    
    except Exception as e:
        return f"エラー対処提案の生成中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"error", "history", "resolution"})
async def get_error_resolution_history(
    deployment_id: str,
    time_range_hours: int = 168  # 7日間
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
        # 注: 実運用ではデータベースから履歴を取得
        # ここでは例示的な実装
        
        from datetime import datetime, timedelta
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        # USER_ACTIVITY_LOG からエラーを抽出（実装例）
        from user_monitoring_tools import USER_ACTIVITY_LOG
        
        error_logs = [
            log for log in USER_ACTIVITY_LOG
            if log['deployment_id'] == deployment_id
            and log.get('error')
            and start_time <= log['timestamp'] <= end_time
        ]
        
        if not error_logs:
            return f"""
## エラー対処履歴

**デプロイメントID**: {deployment_id}
**分析期間**: 過去 {time_range_hours} 時間

✅ この期間中にエラーは記録されていません。
"""
        
        # エラーを種類別に集計
        error_types = {}
        for log in error_logs:
            error_msg = log.get('error_message', 'Unknown error')
            if error_msg not in error_types:
                error_types[error_msg] = {
                    'count': 0,
                    'first_seen': log['timestamp'],
                    'last_seen': log['timestamp'],
                    'affected_users': set()
                }
            error_types[error_msg]['count'] += 1
            error_types[error_msg]['last_seen'] = max(error_types[error_msg]['last_seen'], log['timestamp'])
            error_types[error_msg]['affected_users'].add(log['user_id'])
        
        history = f"""
## エラー対処履歴

**デプロイメントID**: {deployment_id}
**分析期間**: 過去 {time_range_hours} 時間
**総エラー数**: {len(error_logs)}

### 頻出エラー TOP5

"""
        
        sorted_errors = sorted(error_types.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
        
        for i, (error_msg, info) in enumerate(sorted_errors, 1):
            history += f"""
#### {i}. {error_msg[:100]}{'...' if len(error_msg) > 100 else ''}
- **発生回数**: {info['count']}
- **影響ユーザー数**: {len(info['affected_users'])}
- **初回発生**: {info['first_seen'].strftime('%Y-%m-%d %H:%M')} UTC
- **最終発生**: {info['last_seen'].strftime('%Y-%m-%d %H:%M')} UTC

"""
        
        history += """
### 推奨アクション
- 頻出エラーについては `suggest_error_resolution` ツールで対処方法を確認
- 同じエラーが繰り返し発生している場合は根本原因の調査が必要
"""
        
        return history.strip()
    
    except Exception as e:
        return f"エラー対処履歴の取得中にエラーが発生しました: {str(e)}"


@dr_mcp_tool(tags={"error", "diagnosis", "automatic"})
async def diagnose_deployment_issues(
    deployment_id: str
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
        from datarobot.models import Deployment
        from datetime import datetime, timedelta
        
        deployment = Deployment.get(deployment_id=deployment_id)
        
        # 過去24時間のサービス統計を取得
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        service_stats = deployment.get_service_stats(start=start_time, end=end_time)
        
        # 問題リストを初期化
        issues = []
        health_score = 100  # 満点は100点
        
        # 1. エラー率チェック
        total_requests = service_stats.metrics.get('totalRequests', 0)
        total_errors = service_stats.metrics.get('totalErrors', 0)
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        if error_rate > 10:
            issues.append({
                'severity': 'critical',
                'issue': f'高エラー率（{error_rate:.1f}%）',
                'impact': '多数のユーザーリクエストが失敗しています',
                'action': 'エラーログを確認し、原因を特定してください'
            })
            health_score -= 30
        elif error_rate > 5:
            issues.append({
                'severity': 'high',
                'issue': f'中程度のエラー率（{error_rate:.1f}%）',
                'impact': '一部のユーザーリクエストが失敗しています',
                'action': 'エラーパターンを分析してください'
            })
            health_score -= 15
        
        # 2. レイテンシチェック
        avg_latency = service_stats.metrics.get('avgResponseTime', 0)
        if avg_latency > 10000:  # 10秒以上
            issues.append({
                'severity': 'high',
                'issue': f'高レイテンシ（平均 {avg_latency}ms）',
                'impact': 'ユーザー体験が著しく悪化しています',
                'action': 'パフォーマンス最適化が必要です'
            })
            health_score -= 20
        elif avg_latency > 5000:  # 5秒以上
            issues.append({
                'severity': 'medium',
                'issue': f'やや高いレイテンシ（平均 {avg_latency}ms）',
                'impact': 'ユーザー体験が低下している可能性があります',
                'action': 'パフォーマンスを監視してください'
            })
            health_score -= 10
        
        # 3. デプロイメントステータスチェック
        if deployment.status != 'active':
            issues.append({
                'severity': 'critical',
                'issue': f'デプロイメントステータスが異常（{deployment.status}）',
                'impact': 'デプロイメントが正常に動作していません',
                'action': 'デプロイメントの設定を確認してください'
            })
            health_score -= 40
        
        # 診断レポート生成
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        
        # ヘルススコアの評価
        if health_score >= 90:
            health_status = '✅ 優良'
            health_color = '🟢'
        elif health_score >= 70:
            health_status = '⚠️ 注意'
            health_color = '🟡'
        elif health_score >= 50:
            health_status = '⚠️ 警告'
            health_color = '🟠'
        else:
            health_status = '🚨 緊急'
            health_color = '🔴'
        
        report = f"""
## デプロイメント診断レポート

**デプロイメント**: {deployment.label}
**デプロイメントID**: {deployment_id}
**診断時刻**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

### ヘルススコア
{health_color} **{health_score}/100** - {health_status}

"""
        
        if issues:
            report += "### 検出された問題\n\n"
            for i, issue in enumerate(issues, 1):
                report += f"""
{severity_emoji[issue['severity']]} **問題 {i}: {issue['issue']}**
- **重要度**: {issue['severity'].upper()}
- **影響**: {issue['impact']}
- **推奨アクション**: {issue['action']}

"""
        else:
            report += "### ✅ 問題は検出されませんでした\n\n"
            report += "デプロイメントは正常に動作しています。継続的な監視を推奨します。\n"
        
        report += f"""
### サマリー統計（過去24時間）
- **総リクエスト数**: {total_requests:,}
- **エラー数**: {total_errors}
- **エラー率**: {error_rate:.2f}%
- **平均レスポンス時間**: {avg_latency}ms

### 次のステップ
"""
        
        if health_score < 70:
            report += "1. 緊急: 検出された問題に対処してください\n"
            report += "2. `analyze_errors` ツールでエラーの詳細を確認\n"
            report += "3. `get_recent_traces` ツールで最近の実行状況を確認\n"
        else:
            report += "1. 継続的な監視を続けてください\n"
            report += "2. 定期的に `diagnose_deployment_issues` を実行して健全性を確認\n"
        
        return report.strip()
    
    except Exception as e:
        return f"デプロイメント診断中にエラーが発生しました: {str(e)}"
```

### Phase 3: 高度化機能 (将来拡張)

1. **自動アラート設定**
   - エラー率が閾値を超えたら通知
   - パフォーマンス劣化の自動検出

2. **トレンド分析**
   - 時系列データの可視化
   - 異常検知とパターン認識

3. **比較分析**
   - 複数デプロイメント間の比較
   - バージョン間のパフォーマンス比較

4. **根本原因分析**
   - エラーの連鎖関係を分析
   - ボトルネック特定の自動化

---

## 📊 DataRobot監視API リファレンス

### 利用可能なAPI

| API/SDK | 用途 | 主要メソッド |
|---------|------|------------|
| **Deployment API** | デプロイメント情報取得 | `Deployment.get()`, `Deployment.list()` |
| **Service Stats API** | サービスヘルス統計 | `deployment.get_service_stats()` |
| **Data Exploration API** | トレース・予測データ | Data exploration endpoints |
| **OpenTelemetry API** | 詳細トレース情報 | `OtelLogEntry`, `OtelMetricSummary` |
| **Custom Metrics API** | カスタムメトリクス | Custom metrics endpoints |

### APIコード例

```python
# デプロイメント情報取得
from datarobot.models import Deployment

deployment = Deployment.get(deployment_id='698587ff226830d448db7b99')
print(f"Label: {deployment.label}")
print(f"Status: {deployment.status}")

# サービス統計取得
from datetime import datetime, timedelta

end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=24)

service_stats = deployment.get_service_stats(
    start=start_time,
    end=end_time
)

print(f"Total Requests: {service_stats.metrics['totalRequests']}")
print(f"Error Rate: {service_stats.metrics['errorRate']}%")
```

### 監視画面とAPIのマッピング

| UI画面 | データソース | 対応API |
|--------|------------|---------|
| **概要タブ** | デプロイメントメタデータ | `Deployment.get()` |
| **データ探索 > トレース一覧** | OpenTelemetry traces | Data Exploration API |
| **データ探索 > トレース詳細** | Span情報、I/O | OpenTelemetry Trace API |
| **モニタリング > サービスヘルス** | リクエスト統計 | `get_service_stats()` |
| **モニタリング > カスタムメトリクス** | LLMコストなど | Custom Metrics API |

---

## ⚙️ 環境設定

### 1. 必須ツールのインストール

DataRobot codespace環境では以下がプリインストール済み：
- Python 3.10+
- uv (パッケージマネージャー)
- Taskfile (タスクランナー)
- Pulumi (IaC)
- Git

### 2. 依存関係のインストール

#### MCPサーバー依存関係追加

**ファイル**: `mcp_server/pyproject.toml`

```toml
[project]
dependencies = [
    # ... 既存の依存関係
    "datarobot>=3.11.0",  # 🆕 DataRobot Python SDK
]
```

インストールコマンド：
```bash
cd mcp_server
uv pip install datarobot
```

### 3. 環境変数設定

**ファイル**: `mcp_server/.env`

```bash
# 必須: DataRobot認証情報
DATAROBOT_API_TOKEN=[YOUR_DATAROBOT_API_KEY]
DATAROBOT_ENDPOINT=[YOUR_DATAROBOT_ENDPOINT]

# 必須: セッション秘密鍵
SESSION_SECRET_KEY=[YOUR_SESSION_SECRET_KEY]

# オプション: サーバー設定
MCP_SERVER_NAME=datarobot-monitoring-mcp
MCP_SERVER_PORT=8080
MCP_SERVER_LOG_LEVEL=WARNING
APP_LOG_LEVEL=INFO

# オプション: 動的ツール登録
MCP_SERVER_REGISTER_DYNAMIC_TOOLS_ON_STARTUP=true

# オプション: MCP target_type設定
USE_MCP_TARGET_TYPE=true
```

---

## 🔑 重要な設計原則

### copilot-instructions.md 準拠

#### 1. State管理
```python
# ✅ Good: 標準のMessagesStateを使用
StateGraph[MessagesState, None, MessagesState, MessagesState](MessagesState)
```

#### 2. 入力インターフェース
```python
# ✅ Good: プレーンテキストのみ
invoke({"input": "deployment 698587ff のエラー分析"})
```

#### 3. MCPツール定義
```python
# ✅ Good: @dr_mcp_toolデコレータを使用
@dr_mcp_tool(tags={"monitoring", "trace"})
async def get_recent_traces(deployment_id: str, limit: int = 10) -> str:
    """最近のトレース情報を取得"""
    pass
```

#### 4. LLM呼び出し
```python
# ✅ Good: self.llm()を使用
self.llm(preferred_model="datarobot/azure/gpt-4o")
```

#### 5. エラーハンドリング
```python
# ✅ Good: 丁寧なエラーメッセージ
try:
    deployment = Deployment.get(deployment_id=deployment_id)
except Exception as e:
    return f"デプロイメント情報の取得中にエラーが発生しました: {str(e)}"
```

---

## 🚀 開発ワークフロー

### ローカル開発

#### 1. リポジトリクローン
```bash
git clone [repository-url]
cd datarobot-agent-application-main
```

#### 2. 依存関係インストール
```bash
task install
```

#### 3. MCPサーバー起動
```bash
cd mcp_server
task run
```

#### 4. エージェント開発モードで起動
```bash
cd agent
task dev
```

#### 5. テスト実行
```bash
# 監視ツールのテスト
cd mcp_server
pytest app/tests/test_deployment_monitoring_tools.py

# エージェントのテスト
cd agent
pytest tests/test_monitoring_agent.py
```

### デプロイ

```bash
# Pulumi経由でDataRobotにデプロイ
cd infra
pulumi up
```

---

## 🎯 実装の優先順位

### Phase 1: MVP (基本監視機能)
**期間**: 2-3日

- [x] プロジェクト設計書作成
- [ ] 監視ツール実装 (`deployment_monitoring_tools.py`)
  - [ ] `get_deployment_overview`
  - [ ] `get_service_health`
  - [ ] `get_recent_traces`
  - [ ] `analyze_errors`
- [ ] 監視エージェント実装 (`monitoring_agent.py`)
- [ ] 環境変数設定 (`.env`)
- [ ] ローカル動作確認

**成功条件**: 
- "deployment XXX のヘルスチェック" で統計情報が返る
- エラー分析が実行できる
- トレース一覧が取得できる

### Phase 2: ユーザー監視とエラー対処機能
**期間**: 3-4日

- [ ] ユーザー監視ツール実装 (`user_monitoring_tools.py`)
  - [ ] `get_user_usage_stats`
  - [ ] `get_all_users_summary`
  - [ ] ユーザーアクティビティログ機能
- [ ] エラー対処ツール実装 (`error_resolution_tools.py`)
  - [ ] `suggest_error_resolution`
  - [ ] `get_error_resolution_history`
  - [ ] `diagnose_deployment_issues`
- [ ] エラー対処データベースの充実化
- [ ] 統合テスト

**成功条件**:
- ユーザー別の利用統計が正確に取得できる
- エラーメッセージから適切な対処方法が提案される
- 自動診断でデプロイメントの問題が検出できる

### Phase 3: トレース詳細とパフォーマンス分析
**期間**: 2-3日

- [ ] `search_trace_by_id` 実装
- [ ] OpenTelemetry API統合
- [ ] Span階層の可視化
- [ ] Input/Output詳細表示
- [ ] `get_performance_metrics` 実装
- [ ] レイテンシ統計の計算
- [ ] トレンド分析機能
- [ ] ボトルネック特定支援

**成功条件**:
- Trace IDを指定して詳細情報が取得できる
- Span階層が理解しやすい形式で表示される
- パフォーマンス劣化を自動検出できる
- 推奨される最適化アクションが提示される

### Phase 4: 統合とデプロイ
**期間**: 2-3日

- [ ] フロントエンド統合
- [ ] ユーザー認証との統合
- [ ] アクティビティログの永続化（データベース）
- [ ] E2Eテスト
- [ ] DataRobotへのデプロイ
- [ ] ユーザードキュメント作成
- [ ] 運用ガイド作成

---

## 📝 コーディング時の注意点

### Do's ✅

1. **DataRobot SDK のエラーハンドリング**
   ```python
   try:
       deployment = Deployment.get(deployment_id=deployment_id)
   except dr.errors.ClientError as e:
       if e.status_code == 404:
           return f"デプロイメントID {deployment_id} が見つかりません"
       else:
           return f"API エラー: {str(e)}"
   ```

2. **時刻処理の統一**
   ```python
   from datetime import datetime, timezone
   
   # 常にUTCを使用
   end_time = datetime.now(timezone.utc)
   ```

3. **大量データの処理**
   ```python
   # ページネーションを実装
   async def get_all_traces(deployment_id: str, limit: int = 100):
       offset = 0
       all_traces = []
       while len(all_traces) < limit:
           batch = fetch_traces(offset=offset, batch_size=20)
           if not batch:
               break
           all_traces.extend(batch)
           offset += 20
       return all_traces[:limit]
   ```

4. **ツール結果のキャッシュ**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def get_deployment_info_cached(deployment_id: str):
       return Deployment.get(deployment_id=deployment_id)
   ```

5. **ユーザー識別とログ記録**
   ```python
   # FastAPIリクエストからユーザーIDを取得
   from fastapi import Request
   
   async def get_current_user(request: Request) -> str:
       # DataRobot API keyやセッション情報から識別
       api_key = request.headers.get("Authorization")
       # ユーザーIDの抽出ロジック
       return user_id
   
   # アクティビティログ記録
   from user_monitoring_tools import log_user_activity
   
   log_user_activity(
       deployment_id=deployment_id,
       user_id=user_id,
       tool_name="get_service_health",
       query=user_query,
       error=False
   )
   ```

6. **データの永続化（本番運用）**
   ```python
   # 開発時: メモリ内リスト
   USER_ACTIVITY_LOG = []
   
   # 本番時: データベース（PostgreSQL、MongoDB等）またはRedis
   import redis
   r = redis.Redis(host='localhost', port=6379, db=0)
   
   def log_activity_to_redis(activity_data):
       key = f"activity:{activity_data['deployment_id']}:{activity_data['timestamp']}"
       r.setex(key, 86400*7, json.dumps(activity_data))  # 7日間保持
   ```

### Don'ts ❌

1. **認証情報のハードコード**
   ```python
   # ❌ Bad
   api_key = "abc123..."
   
   # ✅ Good
   api_key = os.getenv("DATAROBOT_API_TOKEN")
   ```

2. **同期関数と非同期関数の混在**
   ```python
   # MCPツールは必ずasync
   @dr_mcp_tool(tags={"monitoring"})
   async def my_tool(arg: str) -> str:  # ✅
       pass
   ```

3. **生データをそのまま返す**
   ```python
   # ❌ Bad
   return str(service_stats)  # 生のオブジェクト
   
   # ✅ Good
   return json.dumps(service_stats.metrics, indent=2)  # 整形済みJSON
   ```

---

## 📚 参考リソース

### 公式ドキュメント
- [DataRobot Agentic AI Monitoring](https://docs.datarobot.com/en/docs/agentic-ai/agentic-eval/agentic-tracing.html)
- [DataRobot Python SDK - Deployments](https://datarobot-public-api-client.readthedocs-hosted.com/en/early-access/reference/mlops/deployment.html)
- [OpenTelemetry Tracing](https://docs.datarobot.com/en/docs/agentic-ai/agentic-eval/agentic-tracing.html)
- [DataRobot Service Stats API](https://docs.datarobot.com/en/docs/api/reference/sdk/deployment-management.html)

### テンプレート関連
- `copilot-instructions.md`: 開発ガイドラインと制約事項
- `README.md`: セットアップと基本的な使い方
- `mcp_server/README.md`: MCPサーバー詳細ドキュメント

### 内部構造
- `agent/agent/myagent.py`: リファレンス実装
- `mcp_server/app/tools/user_tools.py`: ツール定義のテンプレート

---

## 💡 使用例

### ユーザークエリ例とエージェントの動作

#### 例1: 基本的なヘルスチェック
```
ユーザー: deployment 698587ff のヘルスチェックして

エージェント:
[get_deployment_overview 実行]
[get_service_health 実行]

デプロイメント "[agent-0206-kj] [agent] Deployment" は正常に稼働しています。

## サービスヘルス（過去24時間）
- 総リクエスト数: 1,234
- エラー数: 12
- 成功率: 99.0%
- 平均レスポンス時間: 3,521ms

✅ 全体的に良好な状態です。
```

#### 例2: エラー調査
```
ユーザー: 最近エラーが増えてる気がする。調べて

エージェント:
[analyze_errors 実行]

過去24時間で23件のエラーが発生しています（前日比+92%）。

## エラー内訳
- データエラー: 18件 (78%)
- システムエラー: 5件 (22%)

⚠️ データエラーが急増しています。

**推奨アクション**:
1. 入力データのスキーマ変更がないか確認
2. 最近のトレースでInput形式を確認
3. `get_recent_traces` で詳細調査を推奨
```

#### 例3: トレース詳細調査
```
ユーザー: trace e8aee2e2ee9bc3f655105bd96769b7ff の詳細を見せて

エージェント:
[search_trace_by_id 実行]

## トレース詳細

**Trace ID**: e8aee2e2ee9bc3f655105bd96769b7ff
**実行時間**: 37,192ms
**ステータス**: Success

### Span階層
```
LangGraph.workflow [35392ms]
  ├─ agent.task [6815ms]
  ├─ mcp.request.initialize [0.52ms]
  └─ mcp.request.tools/list [0.15ms]
```

**注意**: agent.taskの実行時間が長いです。
ツール呼び出しの最適化を検討してください。
```

#### 例4: ユーザー利用状況の確認
```
ユーザー: deployment 698587ff のユーザーごとの利用状況を教えて

エージェント:
[get_user_usage_stats 実行]

## ユーザー利用統計

**分析期間**: 過去 24 時間

### ユーザー別サマリー

#### ユーザー: alice@datarobot.com
- **総リクエスト数**: 45
- **エラー数**: 2
- **エラー率**: 4.4%
- **最も使用されたツール**: get_service_health

#### ユーザー: bob@datarobot.com
- **総リクエスト数**: 23
- **エラー数**: 0
- **エラー率**: 0.0%
- **最も使用されたツール**: analyze_errors

全体的にアクティブな利用が確認できます。
```

#### 例5: エラー対処方法の提案
```
ユーザー: "Deployment not found" エラーの対処方法を教えて

エージェント:
[suggest_error_resolution 実行]

🟠 **デプロイメントが見つかりません**

**重要度**: HIGH

### 対処手順

1. デプロイメントIDが正しいか確認してください
2. DataRobot UIでデプロイメントが存在するか確認
3. デプロイメントが削除されていないか確認
4. アクセス権限があるか確認（共有設定を確認）

### 予防策

- デプロイメントIDをコピー＆ペーストで使用する
- 削除されたデプロイメントのIDを保存しない

### 関連リソース
- [DataRobot トラブルシューティングガイド](https://docs.datarobot.com/...)
```

#### 例6: 自動診断
```
ユーザー: deployment 698587ff に問題がないか診断して

エージェント:
[diagnose_deployment_issues 実行]

## デプロイメント診断レポート

### ヘルススコア
🟢 **92/100** - ✅ 優良

### ✅ 問題は検出されませんでした

デプロイメントは正常に動作しています。継続的な監視を推奨します。

### サマリー統計（過去24時間）
- **総リクエスト数**: 1,234
- **エラー数**: 12
- **エラー率**: 0.97%
- **平均レスポンス時間**: 3,521ms

### 次のステップ
1. 継続的な監視を続けてください
2. 定期的に `diagnose_deployment_issues` を実行して健全性を確認
```

---

## 🤝 開発支援のためのコンテキスト

### このドキュメントの目的

このドキュメントは、LLMベースのコーディングアシスタントが**DataRobotデプロイメント監視エージェントのコンテキストを完全に理解し、適切なコード提案を行える**ように設計されています。

### LLMに期待する支援内容

1. **監視ツールの実装**
   - DataRobot API統合
   - エラーハンドリング
   - マークダウン形式での出力整形

2. **エージェントロジックの最適化**
   - 適切なツール選択
   - 効率的なデータ取得
   - わかりやすい回答生成

3. **テストコード作成**
   - 単体テスト
   - 統合テスト
   - モックデータ生成

4. **ドキュメント作成**
   - APIリファレンス
   - ユーザーガイド
   - トラブルシューティング

---

## 📞 サポート

### 質問やフィードバック
- DataRobot社内Slackチャンネル
- [DataRobot Support](https://docs.datarobot.com/en/docs/get-started/troubleshooting/general-help.html)

### トラブルシューティング
1. DataRobot API認証エラー
   - 環境変数 `DATAROBOT_API_TOKEN` を確認
   - API keyの有効期限を確認

2. デプロイメントID取得エラー
   - デプロイメントが存在するか確認
   - アクセス権限があるか確認

3. トレースデータが取得できない
   - デプロイメントでトレース機能が有効か確認
   - Data Explorationで予測データが保存されているか確認

---

**最終更新**: 2026-02-06  
**バージョン**: v1.0  
**作成者**: DataRobot Agent Development Team

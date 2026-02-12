# CLAUDE.md - DataRobot デプロイメント監視エージェント

## プロジェクト概要

DataRobotのデプロイメント監視をチャット形式で行うエージェントアプリケーション。
UIで複数画面を行き来する代わりに、自然言語で監視情報を確認・分析できる。

## アーキテクチャ

```
Frontend (React) → FastAPI Backend → LangGraph Agent → MCP Server → DataRobot API
```

4コンポーネント構成:
- `agent/` - LangGraph ReActエージェント
- `mcp_server/` - MCPツール定義（DataRobot API呼び出し）
- `fastapi_server/` - REST API・認証・セッション管理
- `frontend_web/` - React + Vite チャットUI

## 開発ルール（厳守）

### State管理
- **必ず `MessagesState` を使用**。カスタムStateは禁止。
```python
StateGraph[MessagesState, None, MessagesState, MessagesState](MessagesState)
```

### エージェント構築
- `create_react_agent` でReActパターンを使用
- LLM呼び出しは `self.llm()` メソッド経由
- プロンプトは `make_system_prompt()` で構築
- ツールは `self.mcp_tools` で自動ロード

```python
create_react_agent(
    self.llm(preferred_model="datarobot/azure/gpt-4o"),
    tools=self.mcp_tools,
    prompt=make_system_prompt(system_prompt_content),
)
```

### 入力/出力
- フロントエンドからは**プレーンテキストのみ**（構造化JSON不可）
- `invoke({"input": "..."})`（単一引数のみ）
- 出力はマークダウン形式、リスト/表はJSON形式でフロントエンドでパース

### MCPツール定義
- `@dr_mcp_tool` デコレータを使用
- **必ず `async` 関数**で定義
- 戻り値は `str`（整形済みマークダウンまたはJSON）
- docstringにArgs/Returnsを記述（ツール発見用）

```python
@dr_mcp_tool(tags={"monitoring", "deployment"})
async def my_tool(deployment_id: str) -> str:
    """ツールの説明。Args: ... Returns: ..."""
    try:
        # 実装
        return formatted_result
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"
```

### エラーハンドリング
- 全ツールで `try/except` 必須
- ユーザーフレンドリーな日本語エラーメッセージを返す
- 生のオブジェクトを返さない（必ず整形する）

### コーディング規約
- 時刻は常にUTC (`datetime.now(timezone.utc)`)
- 認証情報は環境変数から取得（ハードコード禁止）
- MCPツールは必ず `async`
- 大量データにはページネーション実装
- DataRobot SDKのimport: `from datarobot.models import Deployment`

## ファイル配置

| ファイル | 役割 |
|---------|------|
| `agent/agent/myagent.py` | エージェント本体（ReActワークフロー） |
| `agent/agent/config.py` | エージェント設定 |
| `agent/custom.py` | DRUM エントリポイント |
| `mcp_server/app/tools/user_tools.py` | MCPツール定義 |
| `mcp_server/app/main.py` | MCPサーバー起動 |
| `fastapi_server/app/__init__.py` | FastAPIアプリファクトリ |
| `frontend_web/src/` | Reactコンポーネント |

## 実装するMCPツール（Phase別）

### Phase 1: 基本監視（MVP）
- `list_deployments` - デプロイメント一覧（名前検索対応）
- `find_deployment_by_name` - デプロイメント名→ID解決
- `get_deployment_overview` - デプロイメント概要
- `get_service_health` - サービスヘルス統計（正しいAPIフィールド使用）
- `get_recent_traces` - 最近の予測データ一覧（PredictionDataExport経由）
- `search_trace_by_id` - 予測データ詳細（アソシエーションID検索）
- `analyze_errors` - エラーパターン分析
- `get_performance_metrics` - パフォーマンスメトリクス
- `get_custom_metrics` - カスタムメトリクス（LLMコスト、トークン使用量等）

### Phase 2: マルチユーザー・エラー対処
- `get_user_usage_stats` - ユーザー別利用統計
- `get_all_users_summary` - 全ユーザーサマリー
- `suggest_error_resolution` - エラー対処提案
- `get_error_resolution_history` - エラー対処履歴
- `diagnose_deployment_issues` - 自動診断

### Phase 3: 高度な分析
- トレンド分析、根本原因分析

## DataRobot API利用パターン

```python
# デプロイメント取得
deployment = Deployment.get(deployment_id=deployment_id)

# サービス統計（正しいフィールド名）
service_stats = deployment.get_service_stats(start_time=start_time, end_time=end_time)
m = service_stats.metrics
total_requests = m.get('totalRequests')       # 総リクエスト数
total_predictions = m.get('totalPredictions') # 総予測数
execution_time = m.get('executionTime')       # 実行時間(ms)
response_time = m.get('responseTime')         # レスポンス時間(ms)
server_error_rate = m.get('serverErrorRate')  # サーバーエラー率(比率)
user_error_rate = m.get('userErrorRate')      # ユーザーエラー率(比率)
slow_requests = m.get('slowRequests')         # 低速リクエスト数
num_consumers = m.get('numConsumers')         # ユニークユーザー数
median_load = m.get('medianLoad')             # 中央値負荷(req/min)
peak_load = m.get('peakLoad')                 # ピーク負荷(req/min)

# 予測データエクスポート（トレース取得）
from datarobot.models.deployment import PredictionDataExport
export = PredictionDataExport.create(deployment_id=id, start=start, end=end)
datasets = export.fetch_data()
df = datasets[0].get_as_dataframe()

# カスタムメトリクス（REST API経由）
response = dr.Client().get(f"deployments/{id}/customMetrics/")
```

## 開発コマンド

```bash
task install    # 依存関係インストール
task dev        # 全サービス起動（開発モード）
task lint       # リンター実行
task test       # テスト実行
task deploy     # DataRobotへデプロイ
```

## UI/UXガイドライン

- キーカラー: `#81FBA5`
- ダークテーマ: `bg-gray-900`
- WCAG AA基準（コントラスト比 4.5:1）

## 設計書参照

- 詳細設計: `project-deploy.md`
- 開発ガイドライン: `.github/copilot-instructions.md`

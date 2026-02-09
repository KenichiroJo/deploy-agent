# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from typing import Any

from datarobot_genai.core.agents import make_system_prompt
from datarobot_genai.langgraph.agent import LangGraphAgent
from langchain_litellm.chat_models import ChatLiteLLM
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import create_react_agent

from agent.config import Config

config = Config()

SYSTEM_PROMPT = """\
あなたはDataRobotのデプロイメント監視エキスパートです。

## 役割
AIエージェントのデプロイメントを監視し、トレース分析、パフォーマンス診断、
エラー調査を実施します。社内メンバーが迅速に問題を特定・解決できるよう支援します。

## 利用可能なツール

### 基本情報
- **get_deployment_overview**: デプロイメントの概要情報（ID、ステータス、環境）

### サービスヘルス
- **get_service_health**: リクエスト数、エラー率、レスポンス時間
- **analyze_errors**: エラーパターン分析、頻出エラー特定
- **diagnose_deployment_issues**: デプロイメントの問題を自動診断

### トレース分析
- **get_recent_traces**: 最近のトレース一覧（時系列）
- **search_trace_by_id**: 特定トレースの詳細（Span階層、Input/Output）

### パフォーマンス
- **get_performance_metrics**: レイテンシ、スループット、コスト分析

### ユーザー監視
- **get_user_usage_stats**: ユーザー単位の利用統計
- **get_all_users_summary**: 全ユーザーの利用サマリー

### エラー対処支援
- **suggest_error_resolution**: エラーメッセージに基づく対処方法の提案
- **get_error_resolution_history**: 過去のエラーと対処履歴

## ユーザークエリの理解

### クエリパターンとツール選択
1. 「デプロイメント情報を教えて」 → get_deployment_overview
2. 「最近のエラーは？」 → analyze_errors
3. 「パフォーマンスが悪化している」 → get_performance_metrics → get_service_health
4. 「trace ID XXX の詳細」 → search_trace_by_id
5. 「今日のトレース一覧」 → get_recent_traces
6. 「ヘルスチェック」 → get_service_health → analyze_errors
7. 「ユーザーごとの利用状況」 → get_user_usage_stats
8. 「全体の利用状況」 → get_all_users_summary
9. 「このエラーの対処方法は？」 → suggest_error_resolution
10. 「過去のエラー履歴」 → get_error_resolution_history
11. 「問題がないか診断して」 → diagnose_deployment_issues

### デプロイメントIDの扱い
- ユーザーが明示的にIDを指定した場合: そのまま使用
- 「このデプロイメント」「現在のデプロイメント」: コンテキストから推定
- IDが不明な場合: ユーザーに確認を求める

## 回答フォーマット

### 1. 概要回答（簡潔に）
質問に対する直接的な答えを1-2文で提示

### 2. 詳細データ（構造化）
ツールから取得したデータをそのまま表示（マークダウンテーブル、リストなど）

### 3. 推奨アクション（必要に応じて）
- 問題が検出された場合: 具体的な対応手順
- 正常な場合: 継続的な監視ポイント

### 4. 関連情報（オプション）
さらに深掘りできる質問例や、関連ツールの提案

## 重要な原則

1. **データドリブン**: 必ずツールを使って実際のデータを取得してから回答
2. **簡潔性**: 冗長な説明は避け、要点を明確に
3. **実用性**: 社内メンバーが即座にアクションできる情報を提供
4. **文脈理解**: 過去の会話を考慮し、適切なツールを選択
5. **エラーハンドリング**: ツール実行エラー時は、代替手段を提案

## トラブルシューティングフロー

問題報告があった場合の推奨調査順序:
1. get_deployment_overview - 基本状態確認
2. get_service_health - 全体的なヘルスチェック
3. analyze_errors - エラーパターン特定
4. get_recent_traces - 最近の実行状況確認
5. search_trace_by_id - 特定エラーの詳細調査
6. get_performance_metrics - パフォーマンスボトルネック特定
"""


class MyAgent(LangGraphAgent):
    """DataRobotデプロイメント監視に特化したエージェント。
    トレース分析、パフォーマンス診断、エラー調査を自然言語で実行。
    """

    @property
    def workflow(self) -> StateGraph[MessagesState]:
        langgraph_workflow = StateGraph[
            MessagesState, None, MessagesState, MessagesState
        ](MessagesState)
        langgraph_workflow.add_node("monitoring_node", self.monitoring_agent)
        langgraph_workflow.add_edge(START, "monitoring_node")
        langgraph_workflow.add_edge("monitoring_node", END)
        return langgraph_workflow  # type: ignore[return-value]

    @property
    def monitoring_agent(self) -> Any:
        return create_react_agent(
            self.llm(preferred_model="datarobot/azure/gpt-4o"),
            tools=self.mcp_tools,
            prompt=make_system_prompt(SYSTEM_PROMPT),
            name="Deployment Monitoring Agent",
        )

    def llm(
        self,
        preferred_model: str | None = None,
        auto_model_override: bool = True,
    ) -> ChatLiteLLM:
        api_base = self.litellm_api_base(config.llm_deployment_id)
        model = preferred_model
        if preferred_model is None:
            model = config.llm_default_model
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

import { Button } from '@/components/ui/button';
import {
  Activity,
  Server,
  AlertTriangle,
  BarChart3,
  Search,
  Zap,
  ArrowRight,
  Shield,
} from 'lucide-react';

const quickActions = [
  {
    icon: Server,
    label: 'デプロイメント一覧',
    prompt: 'デプロイメント一覧を見せて',
    description: 'アクセス可能な全デプロイメントを確認',
  },
  {
    icon: Activity,
    label: 'ヘルスチェック',
    prompt: '全デプロイメントのヘルスチェックをして',
    description: 'リクエスト数・エラー率・レイテンシを確認',
  },
  {
    icon: AlertTriangle,
    label: 'エラー分析',
    prompt: '最近のエラーを分析して',
    description: '過去24時間のエラーパターンを分析',
  },
  {
    icon: BarChart3,
    label: 'パフォーマンス',
    prompt: 'パフォーマンスメトリクスを見せて',
    description: '実行時間・スループット・負荷分析',
  },
  {
    icon: Search,
    label: 'トレース検索',
    prompt: '最近の予測データを見せて',
    description: '予測データの一覧と詳細検索',
  },
  {
    icon: Zap,
    label: '自動診断',
    prompt: 'デプロイメントの問題を診断して',
    description: '総合的な健全性チェックを実行',
  },
];

interface StartNewChatProps {
  createChat: () => void;
  onQuickAction?: (prompt: string) => void;
}

export function StartNewChat({ createChat, onQuickAction }: StartNewChatProps) {
  const handleQuickAction = (prompt: string) => {
    if (onQuickAction) {
      onQuickAction(prompt);
    } else {
      createChat();
    }
  };

  return (
    <section className="flex min-h-full flex-1 items-center justify-center px-4 py-8">
      <div className="flex w-full max-w-2xl flex-col items-center gap-8">
        {/* Hero Section */}
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-brand/15 mb-1">
            <Shield className="w-7 h-7 text-brand" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight mt-0 mb-0">
            Deployment Monitor
          </h1>
          <p className="text-sm text-muted-foreground max-w-md leading-relaxed">
            {'AIデプロイメントの監視・分析・トラブルシューティングを自然言語で実行できます。下のクイックアクションから始めるか、自由に質問してください。'}
          </p>
        </div>

        {/* Quick Actions Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 w-full">
          {quickActions.map(action => (
            <button
              key={action.label}
              onClick={() => handleQuickAction(action.prompt)}
              className="group flex flex-col items-start gap-2 rounded-xl border border-border/60 bg-card/60 p-4 text-left transition-all hover:bg-accent/80 hover:border-brand/30 hover:shadow-[0_0_20px_-5px] hover:shadow-brand/10 cursor-pointer"
            >
              <div className="flex items-center gap-2 w-full">
                <action.icon className="w-4 h-4 text-brand shrink-0" />
                <span className="text-sm font-medium truncate">{action.label}</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                {action.description}
              </p>
            </button>
          ))}
        </div>

        {/* Start Chat Button */}
        <div className="flex flex-col items-center gap-2">
          <Button
            size="lg"
            onClick={createChat}
            className="gap-2 bg-brand text-brand-foreground hover:bg-brand/90"
          >
            {'新しい会話を始める'}
            <ArrowRight className="w-4 h-4" />
          </Button>
          <p className="text-xs text-muted-foreground">
            {'Enterキーでメッセージを送信'}
          </p>
        </div>
      </div>
    </section>
  );
}

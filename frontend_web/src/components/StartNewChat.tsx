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
    label: '\u30c7\u30d7\u30ed\u30a4\u30e1\u30f3\u30c8\u4e00\u89a7',
    prompt: '\u30c7\u30d7\u30ed\u30a4\u30e1\u30f3\u30c8\u4e00\u89a7\u3092\u898b\u305b\u3066',
    description: '\u30a2\u30af\u30bb\u30b9\u53ef\u80fd\u306a\u5168\u30c7\u30d7\u30ed\u30a4\u30e1\u30f3\u30c8\u3092\u78ba\u8a8d',
  },
  {
    icon: Activity,
    label: '\u30d8\u30eb\u30b9\u30c1\u30a7\u30c3\u30af',
    prompt: '\u5168\u30c7\u30d7\u30ed\u30a4\u30e1\u30f3\u30c8\u306e\u30d8\u30eb\u30b9\u30c1\u30a7\u30c3\u30af\u3092\u3057\u3066',
    description: '\u30ea\u30af\u30a8\u30b9\u30c8\u6570\u30fb\u30a8\u30e9\u30fc\u7387\u30fb\u30ec\u30a4\u30c6\u30f3\u30b7\u3092\u78ba\u8a8d',
  },
  {
    icon: AlertTriangle,
    label: '\u30a8\u30e9\u30fc\u5206\u6790',
    prompt: '\u6700\u8fd1\u306e\u30a8\u30e9\u30fc\u3092\u5206\u6790\u3057\u3066',
    description: '\u904e\u53bb24\u6642\u9593\u306e\u30a8\u30e9\u30fc\u30d1\u30bf\u30fc\u30f3\u3092\u5206\u6790',
  },
  {
    icon: BarChart3,
    label: '\u30d1\u30d5\u30a9\u30fc\u30de\u30f3\u30b9',
    prompt: '\u30d1\u30d5\u30a9\u30fc\u30de\u30f3\u30b9\u30e1\u30c8\u30ea\u30af\u30b9\u3092\u898b\u305b\u3066',
    description: '\u5b9f\u884c\u6642\u9593\u30fb\u30b9\u30eb\u30fc\u30d7\u30c3\u30c8\u30fb\u8ca0\u8377\u5206\u6790',
  },
  {
    icon: Search,
    label: '\u30c8\u30ec\u30fc\u30b9\u691c\u7d22',
    prompt: '\u6700\u8fd1\u306e\u4e88\u6e2c\u30c7\u30fc\u30bf\u3092\u898b\u305b\u3066',
    description: '\u4e88\u6e2c\u30c7\u30fc\u30bf\u306e\u4e00\u89a7\u3068\u8a73\u7d30\u691c\u7d22',
  },
  {
    icon: Zap,
    label: '\u81ea\u52d5\u8a3a\u65ad',
    prompt: '\u30c7\u30d7\u30ed\u30a4\u30e1\u30f3\u30c8\u306e\u554f\u984c\u3092\u8a3a\u65ad\u3057\u3066',
    description: '\u7dcf\u5408\u7684\u306a\u5065\u5168\u6027\u30c1\u30a7\u30c3\u30af\u3092\u5b9f\u884c',
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
            AI\u30c7\u30d7\u30ed\u30a4\u30e1\u30f3\u30c8\u306e\u76e3\u8996\u30fb\u5206\u6790\u30fb\u30c8\u30e9\u30d6\u30eb\u30b7\u30e5\u30fc\u30c6\u30a3\u30f3\u30b0\u3092
            \u81ea\u7136\u8a00\u8a9e\u3067\u5b9f\u884c\u3067\u304d\u307e\u3059\u3002
            \u4e0b\u306e\u30af\u30a4\u30c3\u30af\u30a2\u30af\u30b7\u30e7\u30f3\u304b\u3089\u59cb\u3081\u308b\u304b\u3001\u81ea\u7531\u306b\u8cea\u554f\u3057\u3066\u304f\u3060\u3055\u3044\u3002
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
            \u65b0\u3057\u3044\u4f1a\u8a71\u3092\u59cb\u3081\u308b
            <ArrowRight className="w-4 h-4" />
          </Button>
          <p className="text-xs text-muted-foreground">
            Enter\u30ad\u30fc\u3067\u30e1\u30c3\u30bb\u30fc\u30b8\u3092\u9001\u4fe1
          </p>
        </div>
      </div>
    </section>
  );
}

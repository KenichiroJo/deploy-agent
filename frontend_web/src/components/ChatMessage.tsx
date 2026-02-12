import { memo, useMemo, useState, Component, type ReactNode, type ErrorInfo } from 'react';
import {
  User,
  Bot,
  Cog,
  Hammer,
  Wrench,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CodeBlock } from '@/components/ui/code-block';
import { cn } from '@/lib/utils';
import type { ContentPart, TextUIPart, ToolInvocationUIPart } from '@/types/message';
import { useChatContext } from '@/hooks/use-chat-context';
import type { ChatMessageEvent } from '@/types/events';
import { Badge } from '@/components/ui/badge';

interface ChatMessageErrorBoundaryProps {
  children: ReactNode;
  message: ChatMessageEvent;
}

interface ChatMessageErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ChatMessageErrorBoundary extends Component<
  ChatMessageErrorBoundaryProps,
  ChatMessageErrorBoundaryState
> {
  constructor(props: ChatMessageErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ChatMessageErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ChatMessage render error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className={'flex gap-3 p-4 rounded-lg bg-card'}>
          <div className="flex-shrink-0">
            <div className="w-8 h-8 rounded-full flex items-center justify-center bg-destructive/20 text-destructive">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-medium text-destructive">{'メッセージの表示に失敗しました'}</span>
            </div>
            <CodeBlock code={JSON.stringify(this.props.message, null, 2)} />
            {this.state.error && (
              <div className="text-xs text-muted-foreground my-2">
                <div>{this.state.error.message}</div>
                <div>{this.state.error.stack}</div>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const MarkdownRegExp = /^```markdown\s*|\s*```$/g;

/* ── Custom Markdown Components ── */
const markdownComponents = {
  table: ({ children, ...props }: any) => (
    <div className="md-table-wrap">
      <table {...props}>{children}</table>
    </div>
  ),
  thead: ({ children, ...props }: any) => (
    <thead {...props}>{children}</thead>
  ),
  tbody: ({ children, ...props }: any) => (
    <tbody {...props}>{children}</tbody>
  ),
  tr: ({ children, ...props }: any) => (
    <tr {...props}>{children}</tr>
  ),
  th: ({ children, ...props }: any) => (
    <th {...props}>{children}</th>
  ),
  td: ({ children, ...props }: any) => (
    <td {...props}>{children}</td>
  ),
  h2: ({ children, ...props }: any) => (
    <h2 {...props}>{children}</h2>
  ),
  h3: ({ children, ...props }: any) => (
    <h3 {...props}>{children}</h3>
  ),
  ul: ({ children, ...props }: any) => (
    <ul {...props}>{children}</ul>
  ),
  ol: ({ children, ...props }: any) => (
    <ol {...props}>{children}</ol>
  ),
  li: ({ children, ...props }: any) => (
    <li {...props}>{children}</li>
  ),
  strong: ({ children, ...props }: any) => (
    <strong {...props}>{children}</strong>
  ),
  hr: (props: any) => <hr {...props} />,
  code: ({ inline, children, ...props }: any) => {
    if (inline) {
      return <code className="md-inline-code" {...props}>{children}</code>;
    }
    return <code {...props}>{children}</code>;
  },
};

export function UniversalContentPart({ part }: { part: ContentPart }) {
  if (part.type === 'text') {
    return <TextContentPart part={part} />;
  }
  if (part.type === 'tool-invocation') {
    return <ToolInvocationPart part={part} />;
  }
  return <CodeBlock code={JSON.stringify(part, null, '  ')} />;
}

const MarkdownBlock = memo(({ block, index }: { block: string; index: number }) => {
  if (block.startsWith('```markdown')) {
    const inner = block.replace(MarkdownRegExp, '');
    return (
      <div key={index} className="markdown-block">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {inner}
        </ReactMarkdown>
      </div>
    );
  } else {
    return (
      <ReactMarkdown key={index} remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {block}
      </ReactMarkdown>
    );
  }
});

export function TextContentPart({ part }: { part: TextUIPart }) {
  const blocks = part.text.split(/(```markdown[\s\S]*?```)/g);
  return (
    <>
      {blocks.map((block, i) => (
        <MarkdownBlock key={i} block={block} index={i} />
      ))}
    </>
  );
}

export function ToolInvocationPart({ part }: { part: ToolInvocationUIPart }) {
  const { toolInvocation } = part;
  const { toolName } = toolInvocation;
  const ctx = useChatContext();
  const tool = ctx.getTool(toolName);
  const [isExpanded, setIsExpanded] = useState(false);

  if (tool?.render) {
    return tool.render({ status: 'complete', args: toolInvocation.args });
  }
  if (tool?.renderAndWait) {
    return tool.renderAndWait({
      status: 'complete',
      args: toolInvocation.args,
      callback: event => {
        console.log(event);
      },
    });
  }

  const hasResult = !!toolInvocation.result;

  return (
    <div className="tool-invocation">
      {/* Header */}
      <button
        type="button"
        className="tool-invocation-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? (
          <ChevronDown className="w-3 h-3 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-3 h-3 text-muted-foreground" />
        )}
        <Wrench className="w-3 h-3 text-brand/60" />
        <span className="tool-invocation-name">{toolInvocation.toolName}</span>
        {hasResult ? (
          <CheckCircle2 className="w-3 h-3 text-brand ml-auto" />
        ) : (
          <Loader2 className="w-3 h-3 text-brand/60 ml-auto animate-spin" />
        )}
      </button>

      {/* Collapsible content */}
      {isExpanded && (
        <div className="tool-invocation-body">
          {toolInvocation.args && (
            <div className="tool-invocation-section">
              <div className="tool-invocation-section-label">引数</div>
              <CodeBlock code={JSON.stringify(toolInvocation.args, null, '  ')} />
            </div>
          )}
          {toolInvocation.result && (
            <div className="tool-invocation-section">
              <div className="tool-invocation-section-label">結果</div>
              <CodeBlock code={toolInvocation.result} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ChatMessageContent({
  id,
  role,
  threadId,
  resourceId,
  content,
  type = 'default',
}: ChatMessageEvent) {
  let Icon = useMemo(() => {
    if (role === 'user') {
      return User;
    } else if (role === 'system') {
      return Cog;
    } else if (content.parts.some(({ type }) => type === 'tool-invocation')) {
      return Hammer;
    } else {
      return Bot;
    }
  }, [role, content.parts]);

  return (
    <div
      className={cn('chat-msg', role === 'user' ? 'chat-msg-user' : 'chat-msg-assistant')}
      data-message-id={id}
      data-thread-id={threadId}
      data-resource-id={resourceId}
      data-testid={`${type}-${role}-message-${id}`}
    >
      <div className="chat-msg-avatar-wrap">
        <div
          className={cn(
            'chat-msg-avatar',
            role === 'user'
              ? 'chat-msg-avatar-user'
              : role === 'assistant'
                ? 'chat-msg-avatar-assistant'
                : 'chat-msg-avatar-system'
          )}
        >
          <Icon className="w-3.5 h-3.5" />
        </div>
      </div>
      <div className="chat-msg-body">
        <span className="chat-msg-role">
          {role === 'assistant' ? 'エージェント' : role === 'user' ? 'あなた' : role}
        </span>
        <div className="content">
          {content.parts.map((part, i) => (
            <UniversalContentPart key={i} part={part} />
          ))}
        </div>
      </div>
    </div>
  );
}

export function ChatMessage(props: ChatMessageEvent) {
  return (
    <ChatMessageErrorBoundary message={props}>
      <ChatMessageContent {...props} />
    </ChatMessageErrorBoundary>
  );
}

export const ChatMessagesMemo = memo(ChatMessage);

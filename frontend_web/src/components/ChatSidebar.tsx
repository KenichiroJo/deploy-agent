import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';
import { Skeleton } from '@/components/ui/skeleton';
import {
  MessageSquare,
  MessageSquareText,
  MoreHorizontal,
  Plus,
  Settings,
  LoaderCircle,
  Shield,
  Activity,
  AlertTriangle,
  Server,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ConfirmDialogModal } from '@/components/ConfirmDialog.tsx';
import type { ChatListItem } from '@/api/chat/types';
import { useNavigate } from 'react-router-dom';
import { JSX, useState } from 'react';

export interface ChatSidebarProps {
  isLoading: boolean;
  chatId: string;
  onChatCreate: () => any;
  onChatSelect: (threadId: string) => any;
  onChatDelete: (threadId: string, callbackFn: () => void) => any;
  chats?: ChatListItem[];
  isLoadingDeleteChat: boolean;
}

const sidebarQuickActions = [
  { icon: Server, label: 'デプロイメント一覧', prompt: 'デプロイメント一覧を見せて' },
  { icon: Activity, label: 'ヘルスチェック', prompt: '全デプロイメントのヘルスチェックをして' },
  { icon: AlertTriangle, label: 'エラー分析', prompt: '最近のエラーを分析して' },
];

export function ChatSidebar({
  isLoading,
  chats,
  chatId,
  onChatSelect,
  onChatCreate,
  onChatDelete,
  isLoadingDeleteChat,
}: ChatSidebarProps) {
  const navigate = useNavigate();
  const goToSettings = () => navigate('/settings');
  const [chatToDelete, setChatToDelete] = useState<ChatListItem | null>(null);
  const getIcon = (id: string): JSX.Element => {
    if (id === chatToDelete?.id && isLoadingDeleteChat) {
      return <LoaderCircle className="animate-spin" />;
    }
    if (id === chatId) {
      return <MessageSquareText className="text-brand" />;
    }
    return <MessageSquare />;
  };
  const [open, setOpen] = useState<boolean>(false);

  return (
    <Sidebar className="sidebar">
      <SidebarContent>
        {/* Brand Header */}
        <SidebarGroup>
          <div className="flex items-center gap-2.5 px-2 py-3">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand/15 shrink-0">
              <Shield className="w-4 h-4 text-brand" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-semibold truncate">Deploy Monitor</span>
              <span className="text-[10px] text-muted-foreground leading-tight">DataRobot Agent</span>
            </div>
          </div>
        </SidebarGroup>

        {/* Quick Actions */}
        <SidebarGroup>
          <SidebarGroupLabel className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
            {'クイックアクション'}
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {sidebarQuickActions.map(action => (
                <SidebarMenuItem key={action.label}>
                  <SidebarMenuButton
                    disabled={isLoading}
                    asChild
                    onClick={onChatCreate}
                  >
                    <div className="cursor-pointer">
                      <action.icon className="w-3.5 h-3.5 text-brand/70" />
                      <span className="text-xs">{action.label}</span>
                    </div>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Chats */}
        <SidebarGroup>
          <div className="flex items-center justify-between pr-1">
            <SidebarGroupLabel className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
              {'会話履歴'}
            </SidebarGroupLabel>
            <button
              onClick={onChatCreate}
              disabled={isLoading}
              className="flex items-center justify-center w-5 h-5 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors cursor-pointer"
              title="新しいチャット"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
          <SidebarGroupContent>
            <SidebarMenu id="sidebar-chats">
              {isLoading ? (
                <>
                  <Skeleton className="h-7 rounded-md" />
                  <Skeleton className="h-7 rounded-md" />
                  <Skeleton className="h-7 rounded-md" />
                  <Skeleton className="h-7 rounded-md" />
                </>
              ) : (
                !!chats &&
                chats.map((chat: ChatListItem) => (
                  <SidebarMenuItem key={chat.id} testId={`chat-${chat.id}`}>
                    <SidebarMenuButton
                      asChild
                      isActive={chat.id === chatId}
                      onClick={() => onChatSelect(chat.id)}
                    >
                      <div>
                        {getIcon(chat.id)}
                        <span className="text-xs truncate">{chat.name || '新しいチャット'}</span>
                      </div>
                    </SidebarMenuButton>
                    {chat.initialised && !chatToDelete && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <SidebarMenuAction>
                            <MoreHorizontal />
                          </SidebarMenuAction>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent side="right" align="start">
                          <DropdownMenuItem
                            testId="delete-chat-menu-item"
                            onClick={() => {
                              setChatToDelete(chat);
                              setOpen(true);
                            }}
                          >
                            <span>{'削除'}</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Settings - Bottom */}
        <SidebarGroup className="mt-auto">
          <SidebarMenuItem key="open-settings">
            <SidebarMenuButton disabled={isLoading} asChild onClick={goToSettings}>
              <div className="cursor-pointer">
                <Settings className="w-3.5 h-3.5" />
                <span className="text-xs">{'設定'}</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarGroup>
      </SidebarContent>
      <ConfirmDialogModal
        open={open}
        setOpen={setOpen}
        onSuccess={() => onChatDelete(chatToDelete!.id, () => setChatToDelete(null))}
        onDiscard={() => setChatToDelete(null)}
        chatName={chatToDelete?.name || ''}
      />
    </Sidebar>
  );
}

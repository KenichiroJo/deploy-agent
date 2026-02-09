import { PropsWithChildren } from 'react';
import { v4 as uuid } from 'uuid';
import z from 'zod/v4';
import { Skeleton } from '@/components/ui/skeleton.tsx';
import { Chat } from '@/components/Chat.tsx';
import { useChatContext } from '@/hooks/use-chat-context.ts';
import { useAgUiTool } from '@/hooks/use-ag-ui-tool.ts';
import { useChatList } from '@/hooks/use-chat-list.ts';
import { ChatMessages } from '@/components/ChatMessages.tsx';
import { ChatProgress } from '@/components/ChatProgress.tsx';
import { ChatTextInput } from '@/components/ChatTextInput.tsx';
import { ChatError } from '@/components/ChatError.tsx';
import { ChatMessagesMemo } from '@/components/ChatMessage.tsx';
import { StepEvent } from '@/components/StepEvent.tsx';
import { ThinkingEvent } from '@/components/ThinkingEvent.tsx';
import { ChatProvider } from '@/components/ChatProvider.tsx';
import { StartNewChat } from '@/components/StartNewChat.tsx';
import { ChatSidebar } from '@/components/ChatSidebar.tsx';
import {
  isErrorStateEvent,
  isMessageStateEvent,
  isStepStateEvent,
  isThinkingEvent,
} from '@/types/events.ts';
import { type MessageResponse } from '@/api/chat/types.ts';

const initialMessages: MessageResponse[] = [
  {
    id: uuid(),
    role: 'assistant',
    content: {
      format: 2,
      parts: [
        {
          type: 'text',
          text: `\u30c7\u30d7\u30ed\u30a4\u30e1\u30f3\u30c8\u76e3\u8996\u30a8\u30fc\u30b8\u30a7\u30f3\u30c8\u3067\u3059\u3002\u30c7\u30d7\u30ed\u30a4\u30e1\u30f3\u30c8\u306e\u30d8\u30eb\u30b9\u30c1\u30a7\u30c3\u30af\u3001\u30a8\u30e9\u30fc\u5206\u6790\u3001\u30d1\u30d5\u30a9\u30fc\u30de\u30f3\u30b9\u78ba\u8a8d\u306a\u3069\u3001\u304a\u6c17\u8efd\u306b\u3054\u8cea\u554f\u304f\u3060\u3055\u3044\u3002`,
        },
      ],
    },
    createdAt: new Date(),
    type: 'initial',
  },
];

export function ChatPage({
  chatId,
  setChatId,
}: {
  chatId: string;
  setChatId: (id: string) => void;
}) {
  const {
    hasChat,
    isNewChat,
    chats,
    isLoadingChats,
    addChatHandler,
    deleteChatHandler,
    isLoadingDeleteChat,
  } = useChatList({
    chatId,
    setChatId,
    showStartChat: false,
  });

  return (
    <div className="chat">
      <ChatSidebar
        isLoading={isLoadingChats}
        chatId={chatId}
        chats={chats}
        onChatCreate={addChatHandler}
        onChatSelect={setChatId}
        onChatDelete={deleteChatHandler}
        isLoadingDeleteChat={isLoadingDeleteChat}
      />

      <Loading isLoading={isLoadingChats}>
        {hasChat ? (
          <ChatProvider chatId={chatId} runInBackground={true} isNewChat={isNewChat}>
            <ChatImplementation chatId={chatId} />
          </ChatProvider>
        ) : (
          <StartNewChat createChat={addChatHandler} />
        )}
      </Loading>
    </div>
  );
}

function Loading({ isLoading, children }: { isLoading: boolean } & PropsWithChildren) {
  if (isLoading) {
    return (
      <div className="flex flex-1 flex-col w-full p-4 space-y-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  return children;
}

export function ChatImplementation({ chatId }: { chatId: string }) {
  const {
    sendMessage,
    userInput,
    setUserInput,
    combinedEvents,
    progress,
    deleteProgress,
    isLoadingHistory,
    isAgentRunning,
  } = useChatContext();

  useAgUiTool({
    name: 'alert',
    description: 'Action. Display an alert to the user',
    handler: ({ message }) => alert(message),
    parameters: z.object({
      message: z.string().describe('The message that will be displayed to the user'),
    }),
    background: false,
  });

  // Example for a custom UI widget
  //
  // useAgUiTool({
  //   name: 'weather',
  //   description: 'Widget. Displays weather result to user',
  //   render: ({ args }) => {
  //     return <WeatherWidget {...args} />;
  //   },
  //   parameters: z.object({
  //     temperature: z.number(),
  //     feelsLike: z.number(),
  //     humidity: z.number(),
  //     windSpeed: z.number(),
  //     windGust: z.number(),
  //     conditions: z.string(),
  //     location: z.string(),
  //   }),
  // });

  return (
    <Chat initialMessages={initialMessages}>
      <ChatMessages isLoading={isLoadingHistory} messages={combinedEvents} chatId={chatId}>
        {combinedEvents &&
          combinedEvents.map(m => {
            if (isErrorStateEvent(m)) {
              return <ChatError key={m.value.id} {...m.value} />;
            }
            if (isMessageStateEvent(m)) {
              return <ChatMessagesMemo key={m.value.id} {...m.value} />;
            }
            if (isStepStateEvent(m)) {
              return <StepEvent key={m.value.id} {...m.value} />;
            }
            if (isThinkingEvent(m)) {
              return <ThinkingEvent key={m.type} />;
            }
          })}
      </ChatMessages>
      <ChatProgress progress={progress || {}} deleteProgress={deleteProgress} />
      <ChatTextInput
        userInput={userInput}
        setUserInput={setUserInput}
        onSubmit={sendMessage}
        runningAgent={isAgentRunning}
        showSuggestions={!combinedEvents || combinedEvents.length === 0}
      />
    </Chat>
  );
}

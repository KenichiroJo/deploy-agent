import { Loader2, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Textarea } from '@/components/ui/textarea';
import { KeyboardEvent, useRef, useState } from 'react';

const suggestions = [
  '\u30c7\u30d7\u30ed\u30a4\u30e1\u30f3\u30c8\u4e00\u89a7',
  '\u30d8\u30eb\u30b9\u30c1\u30a7\u30c3\u30af',
  '\u30a8\u30e9\u30fc\u5206\u6790',
  '\u30d1\u30d5\u30a9\u30fc\u30de\u30f3\u30b9\u78ba\u8a8d',
];

export interface ChatTextInputProps {
  onSubmit: (text: string) => any;
  userInput: string;
  setUserInput: (value: string) => void;
  runningAgent: boolean;
  showSuggestions?: boolean;
}

export function ChatTextInput({
  onSubmit,
  userInput,
  setUserInput,
  runningAgent,
  showSuggestions = false,
}: ChatTextInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [isComposing, setIsComposing] = useState(false);

  function keyDownHandler(e: KeyboardEvent) {
    if (
      e.key === 'Enter' &&
      !e.shiftKey &&
      !isComposing &&
      !runningAgent &&
      userInput.trim().length
    ) {
      if (e.ctrlKey || e.metaKey) {
        const el = ref.current;
        e.preventDefault();
        if (el) {
          const start = el.selectionStart;
          const end = el.selectionEnd;

          const newValue = userInput.slice(0, start) + '\n' + userInput.slice(end);
          setUserInput(newValue);
        }
      } else {
        e.preventDefault();
        onSubmit(userInput);
      }
    }
  }

  return (
    <div className="chat-text-input space-y-2">
      {/* Suggestion chips - show when input is empty and not running */}
      {showSuggestions && !userInput.trim() && !runningAgent && (
        <div className="flex flex-wrap gap-1.5">
          {suggestions.map(s => (
            <button
              key={s}
              onClick={() => onSubmit(s)}
              className="inline-flex items-center rounded-full border border-border/60 bg-card/60 px-3 py-1 text-xs text-muted-foreground transition-all hover:bg-brand/10 hover:text-brand hover:border-brand/30 cursor-pointer"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="relative">
        <Textarea
          ref={ref}
          value={userInput}
          onChange={e => setUserInput(e.target.value)}
          onCompositionStart={() => setIsComposing(true)}
          onCompositionEnd={() => setIsComposing(false)}
          onKeyDown={keyDownHandler}
          placeholder="\u30c7\u30d7\u30ed\u30a4\u30e1\u30f3\u30c8\u306b\u3064\u3044\u3066\u8cea\u554f\u3059\u308b..."
          className="pr-12 text-area"
        ></Textarea>
        {runningAgent ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="absolute bottom-2 right-2">
                <Button testId="send-message-disabled-btn" type="submit" size="icon" disabled>
                  <Loader2 className="animate-spin" />
                </Button>
              </span>
            </TooltipTrigger>
            <TooltipContent>\u30a8\u30fc\u30b8\u30a7\u30f3\u30c8\u5b9f\u884c\u4e2d</TooltipContent>
          </Tooltip>
        ) : (
          <Button
            type="submit"
            onClick={() => onSubmit(userInput)}
            className="absolute bottom-2 right-2 bg-brand text-brand-foreground hover:bg-brand/90"
            size="icon"
            testId="send-message-btn"
            disabled={!userInput.trim().length}
          >
            <Send />
          </Button>
        )}
      </div>
    </div>
  );
}

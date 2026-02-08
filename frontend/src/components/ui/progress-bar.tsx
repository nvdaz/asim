import { useMemo } from "react";
import {
  InChatFeedback,
  isContentInChatFeedback,
  Message,
} from "@/hooks/use-chats";
import { cn } from "@/lib/utils";

interface ProgressBarProps {
  messages: (Message | InChatFeedback)[];
  agent: string;
  gap: boolean;
  className?: string;
}

function calculateProgress(
  messages: (Message | InChatFeedback)[],
  agent: string,
  gap: boolean,
): number {
  let feedbackCount = 0;
  let lastCountedFeedbackIndex = -1;

  for (let i = 0; i < messages.length; i++) {
    const item = messages[i];
    if (isContentInChatFeedback(item)) {
      const hasAlternative = !!item.feedback.alternative;

      if (!hasAlternative) {
        // No alternative - counts immediately
        feedbackCount++;
        lastCountedFeedbackIndex = i;
      } else {
        // Has alternative - needs a user message after it to count
        for (let j = i + 1; j < messages.length; j++) {
          const msg = messages[j];
          if (!isContentInChatFeedback(msg) && msg.sender !== agent) {
            feedbackCount++;
            lastCountedFeedbackIndex = i;
            break;
          }
        }
      }
    }
  }

  let userMessagesSinceLastCountedFeedback = 0;
  for (let i = lastCountedFeedbackIndex + 1; i < messages.length; i++) {
    const msg = messages[i];
    if (!isContentInChatFeedback(msg) && msg.sender !== agent) {
      userMessagesSinceLastCountedFeedback++;
    }
  }

  const baseProgress = feedbackCount / 8;
  const maxBonusMessages = gap ? 5 : 4;
  const bonusFraction = 1 / maxBonusMessages;
  const bonusProgress =
    Math.min(userMessagesSinceLastCountedFeedback, maxBonusMessages) *
    (bonusFraction / 8);

  return baseProgress + bonusProgress;
}

export function ProgressBar({
  messages,
  agent,
  gap,
  className,
}: ProgressBarProps) {
  const progress = useMemo(
    () => calculateProgress(messages, agent, gap),
    [messages, agent, gap],
  );
  const clampedProgress = Math.min(Math.max(progress, 0), 1);
  const percentage = Math.round(clampedProgress * 100);
  const isComplete = clampedProgress >= 1;

  return (
    <div className={cn("w-full", className)}>
      <div className="flex justify-end text-xs mb-1">
        {isComplete ? (
          <span className="text-green-600 dark:text-green-400">
            100% complete!{" "}
            <a
              href={import.meta.env.VITE_FEEDBACK_FORM_URL || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-green-700 dark:hover:text-green-300"
            >
              Provide feedback
            </a>
          </span>
        ) : (
          <span>{percentage}% complete</span>
        )}
      </div>
      <div className="h-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full transition-all duration-300 rounded-full",
            isComplete ? "bg-green-500" : "bg-blue-500",
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

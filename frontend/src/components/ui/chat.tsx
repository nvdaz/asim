import { cn } from "@/lib/utils";
import { formatRelative } from "date-fns";
import { motion } from "framer-motion";
import { Fragment, useEffect, useMemo, useRef } from "react";
import { ScrollArea } from "./scroll-area";

interface Message {
  id?: number;
  content: string;
  sender: string;
  avatarUrl?: string;
  isOutgoing?: boolean;
  created_at: string;
}

function capitalize(str: string) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function ChatInterface({
  messages,
  typing,
}: {
  messages: Message[];
  typing: boolean;
}) {
  const chatEnd = useRef<HTMLDivElement>(null);

  const groupedMessages = useMemo(() => {
    const grouped = messages.reduce((acc, msg) => {
      if (acc.length === 0) {
        return [[msg]];
      }

      const lastGroup = acc[acc.length - 1];
      const lastMsg = lastGroup[lastGroup.length - 1];
      if (
        Date.parse(msg.created_at) - Date.parse(lastMsg.created_at) <
        1000 * 60 * 5
      ) {
        lastGroup.push(msg);
      } else {
        acc.push([msg]);
      }

      return acc;
    }, [] as Message[][]);

    return grouped;
  }, [messages]);

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: "instant" });
  }, [chatEnd.current, messages]);

  return (
    <ScrollArea className="h-full w-full">
      <div className="space-y-4 p-4 flex flex-col">
        {groupedMessages.map((group, index) => (
          <Fragment key={index}>
            <div className="text-center text-xs text-gray-500 dark:text-gray-400 mb-4 mt-2">
              {capitalize(
                formatRelative(capitalize(group[0].created_at), new Date())
              )}
            </div>
            {group.map((msg, index) => (
              <ChatBubble
                key={index}
                content={msg.content}
                sender={msg.sender}
                avatarUrl={msg.avatarUrl}
                isOutgoing={msg.sender != "Bob"}
              />
            ))}
          </Fragment>
        ))}
        {typing && (
          <div className="justify-end p-3">
            <TypingIndicator />
          </div>
        )}
      </div>
      <div ref={chatEnd} />
    </ScrollArea>
  );
}

interface ChatBubbleProps {
  content: string;
  sender: string;
  avatarUrl?: string;
  isOutgoing?: boolean;
}

function ChatBubble({ content: message, isOutgoing = false }: ChatBubbleProps) {
  return (
    <div
      className={`flex ${isOutgoing ? "justify-end" : "justify-start"} my-4`}
    >
      <div
        className={`flex ${
          isOutgoing ? "flex-row-reverse" : "flex-row"
        } items-end`}
      >
        <div
          className={`mx-2 ${
            isOutgoing ? "items-end" : "items-start"
          } flex flex-col`}
        >
          <div
            className={`${isOutgoing ? "bg-blue-500" : "bg-secondary"} ${
              isOutgoing ? "text-white" : "text-secondary-foreground"
            } rounded-xl p-3 max-w-xs md:max-w-sm lg:max-w-md w-fit ${
              isOutgoing ? "rounded-br-none" : "rounded-bl-none"
            }`}
          >
            <p className="text-sm">{message}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export function TypingIndicator({
  background = true,
}: {
  background?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center space-x-2 p-3 rounded-xl max-w-fit",
        background && "bg-secondary"
      )}
    >
      <motion.span
        className="w-2 h-2 bg-gray-400 rounded-full"
        animate={{ backgroundColor: ["#D1D5DB", "#9CA3AF", "#D1D5DB"] }}
        transition={{ repeat: Infinity, duration: 1 }}
      />
      <motion.span
        className="w-2 h-2 bg-gray-400 rounded-full"
        animate={{ backgroundColor: ["#D1D5DB", "#9CA3AF", "#D1D5DB"] }}
        transition={{
          repeat: Infinity,
          duration: 1,
          delay: 0.2,
        }}
      />
      <motion.span
        className="w-2 h-2 bg-gray-400 rounded-full"
        animate={{ backgroundColor: ["#D1D5DB", "#9CA3AF", "#D1D5DB"] }}
        transition={{
          repeat: Infinity,
          duration: 1,
          delay: 0.4,
        }}
      />
    </div>
  );
}

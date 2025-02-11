import { cn } from "@/lib/utils";
import { formatRelative } from "date-fns/formatRelative";
import { motion } from "framer-motion";
import { ArrowDownIcon } from "lucide-react";
import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "./button";

export interface Message {
  index?: number;
  id?: number;
  content: string;
  sender: string;
  avatarUrl?: string;
  isOutgoing?: boolean;
  created_at: string;
}

export interface InChatFeedback {
  index?: number;
  feedback: {
    title: string;
    body: string;
  };
  alternative: string | null;
  alternative_feedback: string;
  rating: number | null;
  created_at: string;
}

const isFeedback = (msg: Message | InChatFeedback): msg is InChatFeedback => {
  return "feedback" in msg;
};

function capitalize(str: string) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function ChatInterface({
  id,
  messages,
  typing,
  otherUser,
  handleRate,
  containerRef,
}: {
  id: string;
  messages: (Message | InChatFeedback)[];
  typing: boolean;
  otherUser: string;
  handleRate: (index: number, rating: number) => void;
  containerRef: React.RefObject<HTMLDivElement>;
}) {
  const groupedMessages = useMemo(() => {
    const grouped = messages.reduce((acc, msg, i) => {
      msg.index = i;
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
    }, [] as (Message | InChatFeedback)[][]);

    return grouped;
  }, [messages]);

  const [showScrollButton, setShowScrollButton] = useState(false);

  const handleScroll = useCallback(() => {
    const container = containerRef.current;

    if (!container) return;

    if (
      container.clientHeight + container.scrollTop <
      container.scrollHeight - 200
    ) {
      setShowScrollButton(true);
    } else {
      setShowScrollButton(false);
    }
  }, [containerRef]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener("scroll", handleScroll);
    handleScroll();

    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  const [containerPosition, setContainerPosition] = useState({
    top: 0,
    left: 0,
  });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const updatePosition = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setContainerPosition({
          top: rect.bottom,
          left: rect.right,
        });
      }
    };

    const resizeObserver = new ResizeObserver(updatePosition);
    resizeObserver.observe(container);

    return () => resizeObserver.disconnect();
  }, []);

  const [scrollState, setScrollState] = useState<{
    lastMessageIndex: number;
    lastHeight: number;
  } | null>(null);

  useEffect(() => {
    const container = containerRef.current;

    if (!container) {
      return;
    }

    setScrollState({
      lastMessageIndex: messages.length - 1,
      lastHeight: container.scrollHeight,
    });

    if (scrollState === null) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "instant",
      });
    } else if (scrollState.lastMessageIndex < messages.length - 1) {
      if (isFeedback(messages[messages.length - 1])) {
        container.scrollTo({
          top: scrollState.lastHeight - container.clientHeight + 200,
          behavior: "smooth",
        });
      } else {
        container.scrollTo({
          top: container.scrollHeight - container.clientHeight,
          behavior: "smooth",
        });
      }
    }
  }, [messages.length, containerRef]);

  const [lastClientHeight, setLastClientHeight] = useState(0);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => {
      if (container.clientHeight !== lastClientHeight) {
        const d = container.clientHeight - lastClientHeight;
        const scr = container.scrollTop - d;

        setLastClientHeight(container.clientHeight);

        container.scrollTo({
          top:
            container.scrollHeight -
              container.scrollTop -
              container.clientHeight <
            50
              ? container.scrollHeight
              : scr,
          behavior: "instant",
        });
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, [containerRef, lastClientHeight]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    if (typing) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [typing, containerRef]);

  const [lastId, setLastId] = useState<string | null>(null);

  useEffect(() => {
    if (lastId === null) {
      setLastId(id);
    } else if (lastId !== id) {
      setLastId(id);
      setScrollState(null);
    }
  });

  return (
    <div className="h-full w-full overflow-auto">
      <div
        className="space-y-4 p-4 flex flex-col overflow-auto h-full"
        ref={containerRef}
      >
        <div className="relative">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{
              opacity: showScrollButton ? 1 : 0,
              y: showScrollButton ? 0 : 20,
            }}
            transition={{
              duration: 0.3,
              ease: "easeOut",
            }}
            className="fixed bottom-6 right-6 z-50"
            style={{
              top: `calc(${containerPosition.top}px - 4rem)`,
              left: `calc(${containerPosition.left}px - 4rem)`,
              position: "fixed",
              marginRight: "1.5rem",
              pointerEvents: showScrollButton ? "auto" : "none",
            }}
          >
            <Button
              size="icon"
              className="rounded-full h-8 w-8"
              onClick={() => {
                const container = containerRef.current;
                container?.scrollTo({
                  top: container.scrollHeight,
                  behavior: "smooth",
                });
              }}
            >
              <ArrowDownIcon />
            </Button>
          </motion.div>
          {groupedMessages.map((group, index) => (
            <Fragment key={index}>
              <div className="text-center text-xs text-gray-500 dark:text-gray-400 mb-4 mt-2">
                {capitalize(formatRelative(group[0].created_at, new Date()))}
              </div>
              {group.map((msg, index) =>
                isFeedback(msg) ? (
                  <FeedbackBubble
                    key={index}
                    feedback={msg}
                    handleRate={handleRate}
                    index={msg.index!}
                  />
                ) : (
                  <ChatBubble
                    key={index}
                    content={msg.content}
                    sender={msg.sender}
                    avatarUrl={msg.avatarUrl}
                    isOutgoing={msg.sender !== otherUser}
                  />
                )
              )}
            </Fragment>
          ))}
          {typing && (
            <div className="justify-end p-3">
              <TypingIndicator />
            </div>
          )}
        </div>
      </div>
    </div>
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
    <motion.div
      className={`flex ${isOutgoing ? "justify-end" : "justify-start"} my-4`}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
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
    </motion.div>
  );
}

function FeedbackBubble({
  feedback,
}: {
  feedback: InChatFeedback;
  handleRate: (index: number, rating: number) => void;
  index: number;
}) {
  return (
    <motion.div
      className="w-full flex items-center justify-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <div className="max-w-screen-md my-4">
        <div className="flex items-end">
          <div className="mx-2 flex flex-col">
            <div className="bg-accent text-accent-foreground rounded-md p-3">
              <h2 className="font-semibold">{feedback.feedback.title}</h2>
              <p className="text-sm">{feedback.feedback.body}</p>
              {feedback.alternative && (
                <>
                  <h2 className="mt-4 font-semibold">
                    As An Alternative, You Could Try:
                  </h2>
                  <p className="text-sm rounded-md bg-gray-300 p-2 my-1">
                    {feedback.alternative}
                  </p>
                </>
              )}
              <p className="text-sm">{feedback.alternative_feedback}</p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
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

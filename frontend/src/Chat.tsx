import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, ChevronDown, ChevronLeft, ChevronUp } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChatInterface } from "./components/ui/chat";
import { Loading } from "./components/ui/loading";
import { Skeleton } from "./components/ui/skeleton";
import { Textarea } from "./components/ui/textarea";
import Contacts from "./contacts";
import { useChats } from "./hooks/use-chats";
import { cn } from "./lib/utils";

function Chat() {
  const {
    isConnected,
    isError,
    chats,
    sendChatMessage,
    createChat,
    suggestMessages,
    loadChat,
    markRead,
  } = useChats();

  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const [input, setInput] = useState("");

  const currentChat = useMemo(
    () => (currentChatId ? chats[currentChatId] : null),
    [currentChatId, chats]
  );

  const contacts = useMemo(
    () =>
      Object.values(chats).sort(
        (a, b) => Date.parse(b.last_updated) - Date.parse(a.last_updated)
      ),
    [chats]
  );

  useEffect(() => {
    if (!currentChatId && contacts.length) {
      setCurrentChatId(contacts[0].id);
    }
  }, [contacts, setCurrentChatId]);

  const handleSend = useCallback(() => {
    setShowSuggestions(false);
    sendChatMessage(currentChatId!, input);
    setInput("");
  }, [input, sendChatMessage, currentChatId]);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        handleSend();
        e.preventDefault();
      }
    };

    inputRef.current?.addEventListener("keypress", handleKeyPress);

    return () => {
      inputRef.current?.removeEventListener("keypress", handleKeyPress);
    };
  }, [inputRef.current, handleSend]);

  useEffect(() => {
    if (currentChat && !("messages" in currentChat)) {
      loadChat(currentChatId!);
    }
  }, [currentChat, loadChat]);

  const getSuggestedMessages = useCallback(() => {
    setShowSuggestions(true);
    suggestMessages(currentChatId!);
  }, [currentChatId, suggestMessages]);

  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  }, [input]);

  useEffect(() => {
    setInput("");
    setShowSuggestions(false);
  }, [currentChat]);

  useEffect(() => {
    if (currentChat && currentChat.unread) {
      markRead(currentChat.id);
    }
  }, [currentChat, chats]);

  if (!isConnected) {
    return (
      <div className="container relative h-full flex-col items-center justify-center grid lg:max-w-none lg:grid-cols-2 px-8">
        <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
          <Loading />
          <AnimatePresence mode="wait">
            {isError ? (
              <motion.h1
                key="error"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="text-2xl font-semibold tracking-tight"
              >
                Something went wrong. We're trying to reconnect...
              </motion.h1>
            ) : (
              <motion.h1
                key="loading"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="text-2xl font-semibold tracking-tight"
              >
                Connecting...
              </motion.h1>
            )}
          </AnimatePresence>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-row min-h-[200px] rounded-lg border w-full h-screen">
      <div
        className={cn(
          currentChatId ? "lg:w-[400px] hidden" : "w-full",
          "overflow-hidden bg-secondary lg:block"
        )}
      >
        <Contacts
          chats={contacts}
          handleSelect={setCurrentChatId}
          handleNewChat={createChat}
          selectedChatId={currentChatId}
        />
      </div>
      <div className={cn(!currentChatId && "hidden", "w-full")}>
        <div className="flex flex-col h-full">
          <div className="flex flex-row items-center p-2">
            <Button
              variant="ghost"
              onClick={() => setCurrentChatId(null)}
              size="icon"
              className="mr-4 lg:hidden"
            >
              <ChevronLeft />
            </Button>
            <Avatar>
              <AvatarFallback>B</AvatarFallback>
            </Avatar>
            <h2 className="p-4 font-semibold">{currentChat?.agent}</h2>
          </div>
          <Separator />
          <ChatInterface
            messages={currentChat ? currentChat?.messages || [] : []}
            typing={!!currentChat?.agent_typing}
          />
          <Separator />
          <div className="flex flex-col gap-2 p-4">
            <div className="flex flex-col gap-2 w-full">
              <div>
                {showSuggestions ? (
                  <div>
                    <Button
                      variant="outline"
                      className="float-right"
                      onClick={() => setShowSuggestions(false)}
                    >
                      <span className="pr-1">Hide Suggestions</span>
                      <ChevronDown />
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    className="float-right"
                    onClick={getSuggestedMessages}
                  >
                    <span className="pr-1">Show Suggestions</span>
                    <ChevronUp />
                  </Button>
                )}
              </div>
              <div className="flex flex-col gap-2 items-center">
                {showSuggestions &&
                  (currentChat?.suggestions
                    ? currentChat.suggestions.map((message) => (
                        <button
                          key={message}
                          onClick={() => {
                            setInput(message);
                            setShowSuggestions(false);
                          }}
                          className="border rounded-md px-4 py-2 w-full text-left min-h-10"
                        >
                          {message}
                        </button>
                      ))
                    : Array(3)
                        .fill("")
                        .map((_, i) => (
                          <Skeleton key={i} className="h-10 w-full" />
                        )))}
              </div>
            </div>
            <div className="flex flex-row gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Message"
                ref={inputRef}
                rows={1}
                className="min-h-[30px] max-h-[120px] resize-none"
              />
              {input.trim() && (
                <Button onClick={handleSend} size="icon">
                  <ArrowUp />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chat;

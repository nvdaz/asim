import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, ChevronLeft, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatInterface } from "./components/ui/chat";
import { Loading } from "./components/ui/loading";
import { Skeleton } from "./components/ui/skeleton";
import { Textarea } from "./components/ui/textarea";
import Contacts from "./contacts";

import { useToast } from "@/hooks/use-toast";
import { useAuth } from "./components/auth-provider";
import { chatIsLoaded } from "./hooks/use-chats";
import { useCurrentChat } from "./hooks/use-current-chat";
import { cn } from "./lib/utils";

function Chat() {
  const {
    isConnected,
    isError,
    contacts,
    currentChat,
    sendChatMessage,
    createChat,
    suggestMessages,
    sendViewSuggestion,
    setCurrentChatId,
  } = useCurrentChat();
  const { toast } = useToast();
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const [input, setInput] = useState("");
  const { user } = useAuth();
  const [selectedSuggestion, setSelectedSuggestion] = useState<number | null>(
    null
  );

  const handleSend = useCallback(() => {
    suggestMessages(input);
    setInput("");
  }, [input]);

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

  const resizeTextarea = useCallback(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  }, [inputRef.current]);

  useEffect(() => resizeTextarea(), [input]);

  const sendSuggestion = useCallback(() => {
    if (currentChat && chatIsLoaded(currentChat) && selectedSuggestion) {
      if (
        !!currentChat.suggestions![selectedSuggestion].problem &&
        user!.options.feedback_mode == "on-suggestion"
      ) {
        toast({
          variant: "destructive",
          description:
            "The message you selected needs improvement. Please read the feedback and try selecting another message.",
        });
      } else {
        sendChatMessage(selectedSuggestion);
        setSelectedSuggestion(null);
      }
    }
  }, [currentChat, selectedSuggestion]);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedSuggestion(null);
      } else if (e.key === "Enter") {
        sendSuggestion();
      }
    };

    window.addEventListener("keydown", handleKeyPress);

    return () => {
      window.removeEventListener("keydown", handleKeyPress);
    };
  }, [sendSuggestion]);

  useEffect(() => {
    setInput("");
  }, [currentChat?.id]);

  if (!isConnected) {
    return (
      <div className="container relative h-full flex-col items-center justify-center grid lg:max-w-none lg:grid-cols-2 px-8">
        <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
          {!isError && <Loading />}
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
                Error connecting to server.
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

  if (currentChat && !chatIsLoaded(currentChat)) {
    return <Loading />;
  }

  return (
    <div className="flex flex-row min-h-[200px] rounded-lg border w-full h-screen">
      {currentChat?.loading_feedback && <Loading />}
      <div
        className={cn(
          currentChat ? "lg:w-[400px] hidden" : "w-full",
          "overflow-hidden bg-secondary lg:block"
        )}
      >
        <Contacts
          chats={contacts}
          handleSelect={setCurrentChatId}
          handleNewChat={createChat}
          selectedChatId={currentChat?.id || null}
        />
      </div>
      <div className={cn(!currentChat && "hidden", "w-full")}>
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
            {currentChat && currentChat.agent ? (
              <>
                <Avatar>
                  <AvatarFallback>{currentChat.agent[0]}</AvatarFallback>
                </Avatar>
                <h2 className="p-4 font-semibold">{currentChat.agent}</h2>
              </>
            ) : (
              <>
                <Skeleton className="h-10 w-10 rounded-full" />
                <Skeleton className="h-6 w-40 mx-4 my-4" />
              </>
            )}
          </div>
          <Separator />
          {!(currentChat && "messages" in currentChat) && <Loading />}
          <ChatInterface
            messages={currentChat ? currentChat?.messages || [] : []}
            typing={!!currentChat?.agent_typing}
          />
          <Separator />
          <div className="flex flex-col gap-2 p-4">
            <div className="flex flex-col gap-2 w-full">
              <div className="flex flex-col gap-2 items-center">
                {currentChat?.suggestions ||
                currentChat?.generating_suggestions ? (
                  currentChat?.suggestions ? (
                    selectedSuggestion !== null ? (
                      <div className="flex flex-col gap-2 w-full">
                        {currentChat.suggestions[selectedSuggestion]
                          .feedback && (
                          <div className="flex flex-col gap-2 w-full bg-secondary p-4 rounded-md">
                            <div className="font-semibold">
                              {
                                currentChat.suggestions[selectedSuggestion]
                                  .feedback.title
                              }
                            </div>
                            <div>
                              {
                                currentChat.suggestions[selectedSuggestion]
                                  .feedback.body
                              }
                            </div>
                          </div>
                        )}
                        <div className="flex flex-row gap-2 w-full">
                          <div className="rounded-md border border-input bg-transparent pl-3 text-sm shadow-sm flex flex-row gap-2 items-center w-full">
                            <div className="w-full py-2">
                              {
                                currentChat.suggestions[selectedSuggestion]
                                  .message
                              }
                            </div>
                            <Button
                              size="icon"
                              className="bg-transparent min-w-8 hover:bg-transparent hover:text-red-500 self-end text-black dark:text-white shadow-none"
                              onClick={() => setSelectedSuggestion(null)}
                            >
                              <X />
                            </Button>
                          </div>
                          <Button
                            onClick={sendSuggestion}
                            size="icon"
                            className="min-w-8 self-end"
                          >
                            <ArrowUp />
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="div flex flex-col gap-2 w-full align-end">
                        {currentChat.suggestions.map(({ message }, i) => (
                          <button
                            key={i}
                            onClick={() => {
                              sendViewSuggestion(i);
                              setSelectedSuggestion(i);
                            }}
                            className="border rounded-md px-4 py-2 w-full text-left min-h-10"
                          >
                            {message}
                          </button>
                        ))}
                        <Textarea
                          value=""
                          placeholder="Select an option"
                          ref={inputRef}
                          rows={1}
                          className="min-h-[30px] max-h-[120px] resize-none"
                          disabled
                        />
                      </div>
                    )
                  ) : (
                    <div className="flex flex-col gap-2 w-full">
                      {Array(currentChat.generating_suggestions)
                        .fill("")
                        .map((_, i) => (
                          <Skeleton key={i} className="h-10 w-full" />
                        ))}
                      <Textarea
                        value=""
                        placeholder="Select an option"
                        ref={inputRef}
                        rows={1}
                        className="min-h-[30px] max-h-[120px] resize-none"
                        disabled
                      />
                    </div>
                  )
                ) : (
                  <div className="flex flex-row gap-2 w-full align-end">
                    <Textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Message"
                      ref={inputRef}
                      rows={1}
                      className="min-h-[30px] max-h-[120px] resize-none"
                      disabled={
                        !currentChat ||
                        currentChat.agent_typing ||
                        currentChat.loading_feedback ||
                        currentChat.generating_suggestions > 0
                      }
                    />
                    {input.trim() && (
                      <Button
                        onClick={handleSend}
                        size="icon"
                        className="self-end"
                      >
                        <ArrowUp />
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chat;

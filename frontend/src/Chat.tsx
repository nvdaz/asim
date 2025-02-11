import { useAuth } from "@/components/auth-provider";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { ChatInterface, InChatFeedback, Message } from "@/components/ui/chat";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Loading } from "@/components/ui/loading";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, ChevronLeft, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import invariant from "tiny-invariant";
import { Label } from "./components/ui/label";
import { RadioGroup, RadioGroupItem } from "./components/ui/radio-group";
import Contacts from "./contacts";
import { chatIsLoaded } from "./hooks/use-chats";
import { useCurrentChat } from "./hooks/use-current-chat";
import { cn } from "./lib/utils";

function ChatFeedbackDialog({
  isOpen,
  onSubmit,
}: {
  isOpen: boolean;
  onSubmit: (ratings: { [key: string]: number }) => void;
}) {
  const [rating1, setRating1] = useState<number | null>(null);
  const [rating2, setRating2] = useState<number | null>(null);

  const handleSubmit = useCallback(() => {
    invariant(rating1 !== null && rating2 !== null);
    onSubmit({ rating1, rating2 });
  }, [onSubmit, rating1, rating2]);

  const LABELS = [
    "Not at all",
    "Very slightly",
    "Slightly",
    "Moderately",
    "Quite",
    "Very",
    "Extremely",
  ];

  return (
    <Dialog open={isOpen}>
      <DialogContent hideClose className="min-w-fit">
        <DialogHeader>
          <DialogTitle>Rate the Chat</DialogTitle>
          <DialogDescription>Please rate.</DialogDescription>
        </DialogHeader>
        <div>
          <div className="flex flex-col space-y-2">
            <span>
              So far, how engaging do you find this conversation by this point
              in the dialogue?
            </span>
            <RadioGroup
              className="flex flex-row space-x-4 justify-center"
              onValueChange={(value) => setRating1(parseInt(value))}
            >
              {Array.from({ length: 7 }, (_, i) => (
                <div
                  key={i + 1}
                  className="flex flex-col space-y-1 items-center text-center w-[60px]"
                >
                  <RadioGroupItem
                    value={(i + 1).toString()}
                    id={`option-1-${i + 1}`}
                  />
                  <Label className="text-wrap" htmlFor={`option-${i + 1}`}>
                    {LABELS[i]}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </div>
          <Separator className="my-4" />
          <div className="flex flex-col space-y-2">
            <span>
              So far, how realistic do you find this conversation by this point
              in the dialogue?
            </span>
            <RadioGroup
              className="flex flex-row space-x-4 justify-center"
              onValueChange={(value) => setRating2(parseInt(value))}
            >
              {Array.from({ length: 7 }, (_, i) => (
                <div
                  key={i + 1}
                  className="flex flex-col space-y-1 items-center text-center w-[60px]"
                >
                  <RadioGroupItem
                    value={(i + 1).toString()}
                    id={`option-2-${i + 1}`}
                  />
                  <Label className="text-wrap" htmlFor={`option-${i + 1}`}>
                    {LABELS[i]}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </div>
          <Button
            onClick={handleSubmit}
            disabled={rating1 === null || rating2 === null}
            className="mt-4"
          >
            Submit
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Chat() {
  const { user, token } = useAuth();
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
    handleRate,
    handleCheckpointRate,
    handleIntroductionSeen,
  } = useCurrentChat();
  const { toast } = useToast();
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const [input, setInput] = useState("");
  const [selectedSuggestion, setSelectedSuggestion] = useState<number | null>(
    null
  );
  const navigate = useNavigate();
  const toastDismiss = useRef<() => void>(() => {});

  const [latestMessageIndex, setLatestMessageIndex] = useState<number | null>(
    null
  );

  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!token) {
      navigate("/");
    }
  }, [token]);

  invariant(user, token);

  useEffect(() => {
    if (
      currentChat &&
      chatIsLoaded(currentChat) &&
      latestMessageIndex !== currentChat.messages.length
    ) {
      setLatestMessageIndex(currentChat.messages.length);
    }
  }, [currentChat, latestMessageIndex]);

  useEffect(() => {
    setSelectedSuggestion(null);
  }, [currentChat?.id]);

  const [hasScrolled, setHasScrolled] = useState(false);
  const [hasScrolledGenerated, setHasScrolledGenerated] = useState(false);

  useEffect(() => {
    if (currentChat && chatIsLoaded(currentChat)) {
      if (Array.isArray(currentChat.suggestions)) {
        if (!hasScrolledGenerated) {
          setHasScrolledGenerated(true);
        }
      } else {
        setHasScrolledGenerated(false);
      }
      if (currentChat.generating_suggestions > 0) {
        if (!hasScrolled) {
          setHasScrolled(true);
        }
      } else {
        setHasScrolled(false);
      }
    }
  }, [
    currentChat,
    // @ts-ignore
    currentChat?.generating_suggestions,
    // @ts-ignore
    currentChat?.suggestions,
  ]);

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
    if (
      currentChat &&
      chatIsLoaded(currentChat) &&
      selectedSuggestion !== null
    ) {
      if (
        !!currentChat.suggestions![selectedSuggestion].problem &&
        currentChat!.options.feedback_mode == "on-suggestion"
      ) {
        toast({
          variant: "destructive",
          description:
            "The message you selected needs improvement. Please read the feedback and try selecting another message.",
        });
      } else {
        sendChatMessage(selectedSuggestion);
        setSelectedSuggestion(null);
        toastDismiss.current();
      }
    }
  }, [currentChat, selectedSuggestion]);

  useEffect(() => {
    if (currentChat && chatIsLoaded(currentChat)) {
      if (currentChat.suggestions && currentChat.suggestions.length === 1) {
        setSelectedSuggestion(0);
      }
    }
  }, [selectedSuggestion, currentChat, setSelectedSuggestion]);

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
    <div className="flex flex-row min-h-[200px] rounded-lg border w-screen max-w-screen-2xl justify-self-center h-screen">
      <ChatFeedbackDialog
        isOpen={!!currentChat?.checkpoint_rate}
        onSubmit={handleCheckpointRate}
      />

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
          <div className="flex flex-row items-center p-2 h-16">
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

          {!currentChat?.introduction_seen ? (
            <div className="flex flex-col items-center justify-center p-4 h-full">
              <div className="flex flex-col gap-2 p-8 max-w-lg items-center">
                <p>{currentChat?.introduction}</p>
                <Button
                  className="m-4"
                  onClick={() => {
                    handleIntroductionSeen();
                  }}
                >
                  Start Chat
                </Button>
              </div>
            </div>
          ) : (
            <>
              <ChatInterface
                id={currentChat.id}
                messages={
                  currentChat
                    ? (currentChat?.messages as (Message | InChatFeedback)[]) ||
                      []
                    : []
                }
                handleRate={handleRate}
                typing={!!currentChat?.agent_typing}
                otherUser={currentChat?.agent || ""}
                containerRef={containerRef}
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
                            {currentChat.suggestions.length == 1 && (
                              <p className="text-secondary-foreground font-medium">
                                {(
                                  currentChat?.messages[
                                    currentChat?.messages.length - 1
                                  ] as never as InChatFeedback
                                ).rating !== null
                                  ? "Send this message to clarify and continue the conversation."
                                  : "Provide feedback and then send this message to clarify and continue the conversation."}
                              </p>
                            )}
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
                              <div className="rounded-md border border-input bg-transparent px-3 text-sm shadow-sm flex flex-row gap-2 items-center w-full">
                                <div className="w-full py-2">
                                  {
                                    currentChat.suggestions[selectedSuggestion]
                                      .message
                                  }
                                </div>
                                {currentChat.suggestions.length > 1 && (
                                  <Button
                                    size="icon"
                                    className="bg-transparent min-w-8 hover:bg-transparent self-end text-black dark:text-white hover:text-red-500 dark:hover:text-red-500 shadow-none"
                                    onClick={() => setSelectedSuggestion(null)}
                                  >
                                    <X />
                                  </Button>
                                )}
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
                            <p className="text-secondary-foreground font-medium">
                              Select the best message to send and continue the
                              conversation.
                            </p>
                            {currentChat.suggestions.map(({ message }, i) => (
                              <motion.button
                                key={i}
                                onClick={() => {
                                  sendViewSuggestion(i);
                                  setSelectedSuggestion(i);
                                }}
                                className="border rounded-md px-4 py-2 w-full text-left min-h-10"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: 0.4 }}
                              >
                                {message}
                              </motion.button>
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
                        <motion.div
                          className="flex flex-col gap-2 w-full"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          transition={{ duration: 0.4 }}
                        >
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
                        </motion.div>
                      )
                    ) : (
                      <div className="flex flex-row gap-2 w-full align-end">
                        <Textarea
                          value={input}
                          onChange={(e) => setInput(e.target.value)}
                          placeholder="Write your message here"
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
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Chat;

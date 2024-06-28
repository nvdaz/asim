import { useEffect, useRef } from "react";
import ChatBubble from "./chatBubble";
import Feedback from "./Feedback";
import TypingIndicator from "./TypingIndicator";

import styles from "./index.module.css";

export default function Messages({
  height,
  chatHistory,
  handleClickFeedback,
}) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (containerRef && containerRef.current) {
      containerRef.current.scrollTo({
        behavior: "smooth",
        top: containerRef.current.scrollHeight + 30,
      });
    }
  }, [containerRef?.current?.scrollHeight, chatHistory]);

  // fit chat bubble width to text width
  useEffect(() => {
    const messageDivs = document.querySelectorAll('[data-role="message"]');
    messageDivs?.forEach((m, index) => {
      const range = document.createRange();
      const text = m?.childNodes[0];
      if (text) {
        range.setStartBefore(text);
        range.setEndAfter(text);
        const clientRect = range.getBoundingClientRect();
        m.style.width = `${clientRect.width}px`;
      }
    });
  }, []);

  const messageHistory = (message, index, length) => {
    switch (message.type) {
      case "text":
        return (
          <ChatBubble
            key={index}
            message={message}
            length={length}
            index={index}
          />
        );
      case "feedback":
        return (
          <Feedback
            key={index}
            handleButtonClick={handleClickFeedback}
            title={message.content.title}
            body={message.content.body}
            choice={message.content.choice}
          />
        );
      case "typingIndicator":
        return <TypingIndicator key={index} />;
      default:
        return "";
    }
  };

  return (
    <div
      style={{ height: height }}
      className={styles.wrapper}
      ref={containerRef}
    >
      <div className={styles.messageWrapper}>
        {chatHistory.map((message, index) => {
          return messageHistory(message, index, chatHistory.length);
        })}
      </div>
    </div>
  );
}

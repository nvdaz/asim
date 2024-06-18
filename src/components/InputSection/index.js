import { useState, useRef } from "react";
import SentimentVerySatisfiedOutlinedIcon from "@mui/icons-material/SentimentVerySatisfiedOutlined";
import useMediaQuery from "@mui/material/useMediaQuery";
import EmojiPicker from "emoji-picker-react";
import TextareaAutosize from "./textareaAutosize.js";
import Choice from "./choice.js";

import styles from "./index.module.css";

const Input = ({
  choice,
  setChoice,
  showChoicesSection,
  setShowChoicesSection,
  messages,
  setMessages,
  selectedButton,
  setSelectedButton,
}) => {
  const [isEmojiPickerOpen, setIsEmojiPickerOpen] = useState(false);

  const isMobile = useMediaQuery("(max-width: 400px)");
  const isDesktop = useMediaQuery("(min-width: 800px)");
  const divRef = useRef(null);

  const handleAddEmoji = (e) => {
    setChoice(choice + e.emoji);
  };

  const handleMessageChange = (e) => {
    setChoice(e.target.value);
    setIsEmojiPickerOpen(false);
  };

  const handleButtonClick = (index, message) => {
    setSelectedButton(index);
    setChoice(message);
  };

  const handleSend = () => {
    setMessages([...messages,
      {
        text: choice,
        isSendedText: true,
      },
      {
        text: "Brainstorm? It's always a storm in my brain.",
        isSendedText: false,
      },
    ]);
    setShowChoicesSection(false);
    setChoice("");
  };

  const choices = ["When can we brainstorm for the poster?", "XXXX"];

  const choicesSection = () => {
    return (
      <div className={styles.choicesWrapper}>
        <div>Start the conversation with:</div>
        <div className={styles.choices}>
          {choices.map((c, index) => (
            <Choice
              key={index}
              index={index}
              message={c}
              func={() => handleButtonClick(index, c)}
              selectedButton={selectedButton}
            />
          ))}
        </div>
      </div>
    );
  };

  return (
    <div
      ref={divRef}
      className={styles.wrapper}
      style={{ borderRadius: showChoicesSection ? "18px 18px 0 0" : 0 }}
    >
      {showChoicesSection && choicesSection()}
      <div className={styles.inputWrapper}>
        <SentimentVerySatisfiedOutlinedIcon
          sx={{
            marginBottom: "3px",
            cursor: "pointer",
            height: "32px",
            width: "32px",
          }}
          onClick={() => setIsEmojiPickerOpen(!isEmojiPickerOpen)}
        />
        <div
          className={styles.inputBubble}
          onClick={() => setIsEmojiPickerOpen(false)}
        >
          <TextareaAutosize value={choice} onChange={handleMessageChange} />
        </div>
        <div
          className={styles.sendButton}
          style={{
            backgroundColor: choice.length === 0 ? "#3C3C43" : "#FFB930",
            color: choice.length === 0 ? "#ACACAC" : "#282828",
          }}
          onClick={handleSend}
        >
          Send
        </div>
      </div>
      <EmojiPicker
        open={isEmojiPickerOpen}
        width="100%"
        height={isMobile ? 340 : 300}
        style={{
          "--epr-picker-border-radius": "0",
          "--epr-search-input-bg-color-active": "#333333",
          "--epr-search-input-height": "34px",
          "--epr-emoji-padding": "4px",
          "--epr-header-padding": "7px 10px",
          "--epr-category-navigation-button-size": isMobile ? "25px" : "20px",
          "--epr-category-label-height": "30px",
          "--epr-emoji-size": isMobile ? "30px" : "20px",
          "--epr-preview-height": "45px",
        }}
        theme="dark"
        previewConfig={{
          defaultEmoji: "1f604",
          defaultCaption: "Smile",
          showPreview: isDesktop ? true : false,
        }}
        onEmojiClick={(e) => handleAddEmoji(e)}
      />
    </div>
  );
};

export default Input;

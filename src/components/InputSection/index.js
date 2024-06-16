import { useState, useRef } from "react";
import SentimentVerySatisfiedOutlinedIcon from "@mui/icons-material/SentimentVerySatisfiedOutlined";
import useMediaQuery from "@mui/material/useMediaQuery";
import EmojiPicker from "emoji-picker-react";
import TextareaAutosize from "./textareaAutosize.js";

import styles from "./index.module.css";

const Input = () => {
  const [isEmojiPickerOpen, setIsEmojiPickerOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [selectedButton, setSelectedButton] = useState(null);

  const isMobile = useMediaQuery("(max-width: 400px)");
  const isDesktop = useMediaQuery("(min-width: 800px)");
  const divRef = useRef(null);

  const handleAddEmoji = (e) => {
    setMessage(message + e.emoji);
  };

  const handleMessageChange = (e) => {
    setMessage(e.target.value);
    setIsEmojiPickerOpen(false);
  };

  const handleButtonClick = (index, message) => {
    setSelectedButton(index);
    setMessage(message);
  };

  const choices = ["When can we brainstorm for the poster?", "XXXX"];

  const choicesSection = () => {
    return (
      <div className={styles.choicesWrapper}>
        <div>Start the conversation with:</div>
        <div className={styles.choices}>
          {choices.map((c, index) => (
            <div
              className={
                selectedButton === index
                  ? styles.selectedBtn
                  : styles.selectableBtn
              }
              onClick={() => handleButtonClick(index, c)}
            >
              {c}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div ref={divRef} className={styles.wrapper}>
      {choicesSection()}
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
          <TextareaAutosize value={message} onChange={handleMessageChange} />
        </div>
        <div
          className={styles.sendButton}
          style={{
            backgroundColor: message === "" ? "#3C3C43" : "#FFB930",
            color: message === "" ? "#ACACAC" : "#282828",
          }}
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

import { useState, useRef } from "react";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import Button from "@mui/material/Button";
import SentimentVerySatisfiedOutlinedIcon from "@mui/icons-material/SentimentVerySatisfiedOutlined";
import useMediaQuery from "@mui/material/useMediaQuery";
import EmojiPicker from "emoji-picker-react";
import TextareaAutosize from "./textareaAutosize.js";
import Preview from "./preview";

import styles from "./index.module.css";

const Input = ({ messages, setMessages }) => {
  const [showPreview, setShowPreview] = useState(false);
  const [isEmojiPickerOpen, setIsEmojiPickerOpen] = useState(false);
  const [message, setMessage] = useState("");

  const isMobile = useMediaQuery("(max-width: 400px)");
  const isDesktop = useMediaQuery("(min-width: 800px)");
  const divRef = useRef(null);
  /* alternative proposal
  const [message, setMessage] = useState(
    "we can do canoeing and scuba diving, but it is a little expensive. you think you can afford it?"
  );

  const handleMessageChange = (e) => {
    setMessage(e.target.textContent);
  }; */

  const handleAddEmoji = (e) => {
    setMessage(message + e.emoji);
  };

  const handleMessageChange = (e) => {
    console.log("?");
    setMessage(e.target.value);
    setIsEmojiPickerOpen(false);
  };

  /* alternative proposal
  const handlePaste = (e) => {
    e.preventDefault(); // Prevent default paste behavior
    // Get plain text from clipboard
    const text = (e.clipboardData || window.clipboardData).getData(
      "text/plain"
    );
    document.execCommand("insertText", false, text);
  };

  const content = () => {
    return showPreview ? (
      <div>
        we can do canoeing and scuba diving, but it is a little expensive.
        <div style={{ textDecoration: "underline" }}>
          you think you can afford it?
        </div>
      </div>
    ) : (
      <div>
        we can do canoeing and scuba diving, but it is a little expensive.
        you think you can afford it?
      </div>
    );
  }; */

  return (
    <div
      ref={divRef}
      className={styles.wrapper}
      style={{ borderRadius: showPreview ? "18px 18px 0 0" : 0 }}
    >
      {showPreview && <Preview setShowPreview={setShowPreview} />}

      <div className={styles.inputWrapper}>
        <Button
          disableRipple
          disabled={message === ""}
          sx={{
            backgroundColor: "#387D21",
            color: "white",
            textTransform: "none",
            height: "35px",
            borderRadius: "8px",
            fontFamily: "Roboto, Open Sans, Lato, sans-serif",
            marginBottom: "1.5px",
            "&:hover": {
              backgroundColor: "#316520",
            },
            "&:disabled": {
              backgroundColor: "#5C5D5B",
              color: "#1E1E1E",
            },
          }}
          onClick={() => {
            setShowPreview(true);
            setIsEmojiPickerOpen(false);
          }}
        >
          Preview
        </Button>
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
          {/* alternative proposal
          <div
            contentEditable={true}
            className={styles.textArea}
            onInput={handleMessageChange}
            onPaste={handlePaste}
          >
            {content()}
          </div> */}
          <button
            className={styles.inputArrowBtn}
            style={{
              display: message === "" ? "none" : "flex",
            }}
          >
            <ArrowUpwardIcon
              style={{ cursor: "pointer" }}
              onClick={() => {
                setMessages([
                  ...messages,
                  {
                    text: message,
                    isSendedText: true,
                  },
                ]);
                setMessage("");
                setIsEmojiPickerOpen(false);
                setShowPreview(false);
              }}
            />
          </button>
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

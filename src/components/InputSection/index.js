import { useState } from "react";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import Button from "@mui/material/Button";
import copy from "copy-to-clipboard";
import TextareaAutosize from "./textareaAutosize.js";
import Preview from "./preview";

import styles from "./index.module.css";

const Input = ({ messages, setMessages }) => {
  const [showPreview, setShowPreview] = useState(false);
  const [message, setMessage] = useState(
    "we can do canoeing and scuba diving, but it is a little expensive. you think you can afford it?",
  );

  const handleMessageChange = (e) => {
    setMessage(e.target.textContent);
  };

  const handlePaste = (e) => {
    e.preventDefault(); // Prevent default paste behavior
    // Get plain text from clipboard
    const text = (e.clipboardData || window.clipboardData).getData(
      "text/plain",
    );
    copy(text);
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
        we can do canoeing and scuba diving, but it is a little expensive. you
        think you can afford it?
      </div>
    );
  };

  return (
    <div
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
          onClick={() => setShowPreview(true)}
        >
          Preview
        </Button>

        <img
          style={{ marginBottom: "3px" }}
          alt="emoji"
          loading="lazy"
          src="https://cdn.builder.io/api/v1/image/assets/TEMP/fbbd15675a5855099ad8823b00110cc413b4be568307edd3f47f79c662a25943?apiKey=2e75a4c13cd54e0ba9836b7a2442a820&"
          className="shrink-0 self-stretch my-auto w-8 aspect-square"
        />
        <div className={styles.inputBubble}>
          {/* <TextareaAutosize value={message} onChange={handleMessageChange} /> */}
          <div
            contentEditable={true}
            className={styles.textArea}
            onInput={handleMessageChange}
            onPaste={handlePaste}
          >
            {content()}
          </div>
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
              }}
            />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Input;

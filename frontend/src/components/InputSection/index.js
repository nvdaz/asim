import { useState, useRef } from "react";
import SentimentVerySatisfiedOutlinedIcon from "@mui/icons-material/SentimentVerySatisfiedOutlined";
import useMediaQuery from "@mui/material/useMediaQuery";
import EmojiPicker from "emoji-picker-react";
import TextareaAutosize from "./textareaAutosize.js";
import ChoicesSection from "./choice.js";
import { Post } from "../../utils/request";

import styles from "./index.module.css";

const Input = ({
  choice,
  setChoice,
  showChoicesSection,
  setShowChoicesSection,
  chatHistory,
  setChatHistory,
  selectedButton,
  setSelectedButton,
  initOptions,
  conversationID,
  setShowProgress,
}) => {
  const [isEmojiPickerOpen, setIsEmojiPickerOpen] = useState(false);
  const [options, setOptions] = useState(initOptions);
  const [selectedOption, setSelectedOption] = useState(null);

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
    
    if (selectedOption === null) {
      setSelectedOption([index, message]);
      let optionsCopy = options;
      delete optionsCopy[index];
      setOptions(optionsCopy);
    }
    else {
      let optionsCopy = options;
      delete optionsCopy[index];
      setSelectedOption([index, message]);
      options[selectedOption[0]] = selectedOption[1];
      setOptions(optionsCopy);
    }
  };

  const fetchData = async (option = selectedButton) => {
    const next = await Post(
      `conversations/${conversationID}/next?option=${option}`
    );
    return next;
  };

  const handleSend = async () => {
    const oldHistoryWithIndicator = [
      ...chatHistory,
      {
        type: "text",
        isSentByUser: true,
        content: choice,
      },
      {
        type: "typingIndicator",
        isSentByUser: false,
      },
    ];

    const oldHistory = [
      ...chatHistory,
      {
        type: "text",
        isSentByUser: true,
        content: choice,
      },
    ];

    setShowChoicesSection(false);
    setChoice("");
    setSelectedButton(null);
    setSelectedOption(null);
    setShowProgress(true);

    setTimeout(async () => {
      setShowProgress(false);
      setChatHistory(oldHistoryWithIndicator);

      const reply = await fetchData();

      if (!reply) {
        console.log("error");
        return;
      }

      const respondedContent = reply?.content;
      const nextFetchedContent = await fetchData();
      let nextFetchedContent2 = null;
      let feedbackContent = "";

      if (nextFetchedContent.type === "feedback") {
        feedbackContent = nextFetchedContent.content;
        if (!nextFetchedContent.content["follow_up"]) {
          nextFetchedContent2 = await fetchData();
          setOptions({ 0: nextFetchedContent2.content.choice });
          setShowChoicesSection(true);
        }
      } else if (nextFetchedContent.type === "np") {
        setShowChoicesSection(true);
        setOptions(Object.assign({}, nextFetchedContent.options));
      }

      let newHistory;

      if (feedbackContent !== "") {
        newHistory = [
          ...oldHistory,
          {
            type: "text",
            isSentByUser: false,
            content: respondedContent,
          },
          {
            type: "feedback",
            content: {
              body: feedbackContent.body,
              choice: feedbackContent["follow_up"],
              title: feedbackContent.title,
            },
          },
        ];
      } else {
        newHistory = [
          ...oldHistory,
          {
            type: "text",
            isSentByUser: false,
            content: respondedContent,
          },
        ];
      }

      setChatHistory(newHistory);
    }, 1500);
  };

  return (
    <div
      ref={divRef}
      className={styles.wrapper}
      style={{ borderRadius: showChoicesSection ? "18px 18px 0 0" : 0 }}
    >
      {showChoicesSection && (
        <ChoicesSection
          options={options}
          handleButtonClick={handleButtonClick}
        />
      )}
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

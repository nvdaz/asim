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
  const [showChoicesSection, setShowChoicesSection] = useState(true);

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
    } else {
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

  const feedbackWithNoFollowUpFollowedByNP = (
    nextFetched,
    selectionResultContent
  ) => {
    // feedback would always not have follow_up
    console.log("feedbackWithNoFollowUpFollowedByNP");
    setOptions(Object.assign({}, nextFetched.data.options));
    setShowChoicesSection(true);
    return [
      {
        type: "feedback",
        content: {
          body: selectionResultContent.body,
          title: selectionResultContent.title,
        },
      },
    ];
  };

  const feedbackWithNoFollowUpFollowedByApAndNp = async (
    selectionResultContent,
    nextFetched
  ) => {
    console.log(
      "feedbackWithNoFollowUpFollowedByAp",
      selectionResultContent,
      nextFetched
    );
    const nextFetchedContent2 = await fetchData();
    setOptions(Object.assign({}, nextFetchedContent2.data.options));
    setShowChoicesSection(true);

    return [
      {
        type: "feedback",
        content: {
          body: selectionResultContent.body,
          choice: selectionResultContent.follow_up,
          title: selectionResultContent.title,
        },
      },
      {
        type: "text",
        isSentByUser: false,
        content: nextFetched.content,
      },
    ];
  };

  const apFollowedByFeedback = async (
    nextFetched,
    oldHistory,
    selectionResultContent
  ) => {
    console.log("apFollowedByFeedback");
    // ap followed by feedback with no follow_up
    if (!nextFetched.content.follow_up) {
      const nextFetched2 = await fetchData();

      return [
        ...oldHistory,
        {
          type: "text",
          isSentByUser: false,
          content: selectionResultContent,
        },
        ...(nextFetched2.data.type === "ap"
          ? await feedbackWithNoFollowUpFollowedByApAndNp(
              selectionResultContent,
              nextFetched2.data
            )
          : await feedbackWithNoFollowUpFollowedByNP(
              nextFetched2.data,
              selectionResultContent
            )),
      ];
    } else {
      console.log("apFollowedByFeedbackWithFollowUp");
      return [
        ...oldHistory,
        {
          type: "text",
          isSentByUser: false,
          content: selectionResultContent.content,
        },
        {
          type: "feedback",
          content: {
            body: nextFetched.content.body,
            choice: nextFetched.follow_up,
            title: nextFetched.content.title,
          },
        },
      ];
    }
  };

  const returnNewHistory = async (
    oldHistory,
    selectionResultType,
    selectionResultContent
  ) => {
    if (selectionResultType === "feedback") {
      if (selectionResultContent?.follow_up) {
        console.log("1");
        return [
          ...oldHistory,
          {
            type: "feedback",
            content: {
              body: selectionResultContent.body,
              choice: selectionResultContent.follow_up,
              title: selectionResultContent.title,
            },
          },
        ];
      }
    }

    const nextFetched = await fetchData();

    // if the first call fetched feedback with no follow up
    if (selectionResultType === "feedback") {
      if (nextFetched.data.type === "ap") {
        setChatHistory([
          ...oldHistory,
          {
            type: "feedback",
            content: {
              body: selectionResultContent.body,
              title: selectionResultContent.title,
            },
          },
          {
            type: "typingIndicator",
            isSentByUser: false,
          },
        ]);

        return [
          ...oldHistory,
          ...(await feedbackWithNoFollowUpFollowedByApAndNp(
            selectionResultContent,
            nextFetched.data
          )),
        ];
      } else {
        return feedbackWithNoFollowUpFollowedByNP(
          nextFetched,
          oldHistory,
          selectionResultContent
        );
      }
    }

    if (selectionResultType === "ap") {
      if (nextFetched.data.type === "feedback") {
        return await apFollowedByFeedback(
          nextFetched.data,
          oldHistory,
          selectionResultContent
        );
      } else if (nextFetched.data.type === "np") {
        console.log("4");
        setOptions(Object.assign({}, nextFetched.data.options));
        setShowChoicesSection(true);
        return [
          ...oldHistory,
          {
            type: "text",
            isSentByUser: false,
            content: selectionResultContent,
          },
        ];
      }
    }

    return [];
  };

  const resetStates = () => {
    setShowChoicesSection(false);
    setChoice("");
    setSelectedButton(null);
    setSelectedOption(null);
    setShowProgress(true);
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

    resetStates();

    setTimeout(async () => {
      setShowProgress(false);
      setChatHistory(oldHistory);

      const selectionResult = await fetchData();
      if (!selectionResult.ok) {
        console.log("error");
        return;
      }
      const selectionResultType = selectionResult.data.type;

      if (selectionResultType !== "feedback") {
        setChatHistory(oldHistoryWithIndicator);
      }

      setChatHistory(
        await returnNewHistory(
          oldHistory,
          selectionResultType,
          selectionResult.data?.content
        )
      );
    }, 1500);
  };

  return (
    <div
      ref={divRef}
      className={styles.wrapper}
      style={{
        borderRadius:
          showChoicesSection && Object.keys(options).length > 0
            ? "18px 18px 0 0"
            : 0,
      }}
    >
      {showChoicesSection && Object.keys(options).length > 0 && (
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
          <TextareaAutosize
            value={choice}
            onChange={handleMessageChange}
            placeholder={"Choose an option to send"}
          />
        </div>
        <div
          className={styles.sendButton}
          style={{
            backgroundColor: choice.length === 0 ? "#3C3C43" : "#FFB930",
            color: choice.length === 0 ? "#ACACAC" : "#282828",
            cursor: choice.length === 0 ? "default" : "pointer",
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

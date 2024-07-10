import { useState } from "react";
import Inputs from "../InputSection/index.js";
import Messages from "../messages/index.js";
import LinearProgress from "@mui/material/LinearProgress";
import handleSend from "../InputSection/util/handleSend";

const InputAndMessages = ({ headerHeight, initData }) => {
  const [chatHistory, setChatHistory] = useState(
    initData.is_user_initiated
      ? []
      : [
          {
            type: "text",
            isSentByUser: false,
            content: initData.ap_message,
          },
        ]
  );
  const [choice, setChoice] = useState("");
  const [selectedButton, setSelectedButton] = useState(null);
  const [showProgress, setShowProgress] = useState(false);

  const handleClickFeedback = (index, message) => {
    setSelectedButton(index);
    setChoice(message);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: `calc(100vh - ${headerHeight}px)`,
      }}
    >
      {showProgress && (
        <LinearProgress sx={{ position: "absolute", width: "100%" }} />
      )}
      <Messages
        chatHistory={chatHistory}
        handleClickFeedback={handleClickFeedback}
      />
      <Inputs
        handleSend={handleSend(
          chatHistory,
          setChatHistory,
          setShowProgress,
          choice,
          setChoice,
          selectedButton,
          setSelectedButton,
          initData.id
        )}
        choice={choice}
        setChoice={setChoice}
        setSelectedButton={setSelectedButton}
        initOptions={Object.assign({}, initData.options)}
      />
    </div>
  );
};

export default InputAndMessages;

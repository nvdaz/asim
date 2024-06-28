import { useState, useCallback } from "react";
import Inputs from "../InputSection/index.js";
import Messages from "../messages/index.js";
import LinearProgress from "@mui/material/LinearProgress";

const InputAndMessages = ({ headerHeight, initData }) => {
  const [chatHistory, setChatHistory] = useState([]);
  const [choice, setChoice] = useState("");
  const [selectedButton, setSelectedButton] = useState(null);
  const [showProgress, setShowProgress] = useState(false);

  const handleClickFeedback = (index, message) => {
    setSelectedButton(index);
    setChoice(message);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: `calc(100vh - ${headerHeight}px)`}}>
      {showProgress && (
        <LinearProgress sx={{ position: "absolute", width: "100%" }} />
      )}
      <Messages
        chatHistory={chatHistory}
        handleClickFeedback={handleClickFeedback}
      />
      <Inputs
        choice={choice}
        setChoice={setChoice}
        chatHistory={chatHistory}
        setChatHistory={setChatHistory}
        selectedButton={selectedButton}
        setSelectedButton={setSelectedButton}
        initOptions={Object.assign({}, initData.options)}
        conversationID={initData.id}
        setShowProgress={setShowProgress}
      />
    </div>
  );
};

export default InputAndMessages;

import { useState, useCallback } from "react";
import Inputs from "../InputSection/index.js";
import Messages from "../messages/index.js";
import LinearProgress from "@mui/material/LinearProgress";

const InputAndMessages = ({ headerHeight, initData }) => {
  const [inputHeight, setInputHeight] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [choice, setChoice] = useState("");
  const [selectedButton, setSelectedButton] = useState(null);
  const [showProgress, setShowProgress] = useState(false);

  const input = useCallback((node) => {
    if (!node) return;
    const resizeObserver = new ResizeObserver(() => {
      setInputHeight(node.getBoundingClientRect().height);
    });
    resizeObserver.observe(node);
  }, []);

  const handleClickFeedback = (index, message) => {
    setSelectedButton(index);
    setChoice(message);
  };

  return (
    <div style={{ position: "relative" }}>
      {showProgress && (
        <LinearProgress sx={{ position: "absolute", width: "100%" }} />
      )}
      <Messages
        height={`calc(100vh - ${headerHeight}px - ${inputHeight}px - 3rem)`}
        chatHistory={chatHistory}
        handleClickFeedback={handleClickFeedback}
      />
      <div ref={input}>
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
    </div>
  );
};

export default InputAndMessages;

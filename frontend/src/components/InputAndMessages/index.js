import { useState, useCallback } from "react";
import Inputs from "../InputSection/index.js";
import Messages from "../messages/index.js";

const InputAndMessages = ({ headerHeight, initData }) => {
  const [inputHeight, setInputHeight] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [showChoicesSection, setShowChoicesSection] = useState(true);
  const [choice, setChoice] = useState("");
  const [selectedButton, setSelectedButton] = useState(null);

  const input = useCallback(
    (node) => {
      if (node !== null) {
        setInputHeight(node.getBoundingClientRect().height);
      }
    },
    [showChoicesSection]
  );

  return (
    <div>
      <Messages
        height={`calc(100vh - ${headerHeight}px - ${inputHeight}px - 3rem)`}
        chatHistory={chatHistory}
        setChatHistory={setChatHistory}
        choice={choice}
        setChoice={setChoice}
        selectedButton={selectedButton}
        setSelectedButton={setSelectedButton}
        initData={initData}
      />
      <div ref={input}>
        <Inputs
          choice={choice}
          setChoice={setChoice}
          showChoicesSection={showChoicesSection}
          setShowChoicesSection={setShowChoicesSection}
          chatHistory={chatHistory}
          setChatHistory={setChatHistory}
          selectedButton={selectedButton}
          setSelectedButton={setSelectedButton}
          initOptions={initData.options}
          conversationID={initData.id}
        />
      </div>
    </div>
  );
};

export default InputAndMessages;

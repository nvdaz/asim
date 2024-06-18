import { useState, useCallback } from "react";
import Inputs from "../InputSection/index.js";
import Messages from "../messages/index.js";

const InputAndMessages = ({ headerHeight }) => {
  const [inputHeight, setInputHeight] = useState(null);
  const [messages, setMessages] = useState([]);
  const [showChoicesSection, setShowChoicesSection] = useState(true);
  const [choice, setChoice] = useState('');
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
        messages={messages}
        setMessages={setMessages}
        selectedButton={selectedButton}
        setSelectedButton={setSelectedButton}
      />
      <div ref={input}>
        <Inputs
          choice={choice}
          setChoice={setChoice}
          showChoicesSection={showChoicesSection}
          setShowChoicesSection={setShowChoicesSection}
          messages={messages}
          setMessages={setMessages}
          selectedButton={selectedButton}
          setSelectedButton={setSelectedButton}
        />
      </div>
    </div>
  );
};

export default InputAndMessages;

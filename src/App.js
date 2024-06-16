import { useState, useCallback } from "react";
import Header from "./components/header";
import Inputs from "./components/InputSection";
import Messages from "./components/messages";
import "./App.css";

function App() {
  const [inputHeight, setInputHeight] = useState(null);
  const [headerHeight, setHeaderHeight] = useState(null);
  const [messages, setMessages] = useState([]);

  const input = useCallback((node) => {
    if (node !== null) {
      setInputHeight(node.getBoundingClientRect().height);
    }
  }, []);

  const header = useCallback((node) => {
    if (node !== null) {
      setHeaderHeight(node.getBoundingClientRect().height);
    }
  }, []);

  return (
    <div className="wrapper">
      <div ref={header}>
        <Header />
      </div>
      <Messages
        messages={messages}
        inputHeight={inputHeight}
        headerHeight={headerHeight}
      />
      <div ref={input}>
        <Inputs messages={messages} setMessages={setMessages} />
      </div>
    </div>
  );
}

export default App;

import { useState, useRef } from "react";

import TextareaAutosize from "./textareaAutosize.js";
import ChoicesSection from "./choice.js";

import styles from "./index.module.css";

const Input = ({
  allowCustomInput = false,
  inputPlaceholder,
  explanationText,
  handleSend,
  choice,
  setChoice,
  setSelectedButton,
  options,
  setOptions,
}) => {
  const [selectedOption, setSelectedOption] = useState(null);
  const [showChoicesSection, setShowChoicesSection] = useState(true);

  const divRef = useRef(null);

  const handleMessageChange = (e) => {
    allowCustomInput && setChoice(e.target.value);
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
          explanationText={explanationText}
          options={options}
          handleButtonClick={handleButtonClick}
        />
      )}
      <div className={styles.inputWrapper}>
        <div className={styles.inputBubble}>
          <TextareaAutosize
            value={choice}
            onChange={handleMessageChange}
            placeholder={inputPlaceholder}
          />
        </div>
        <div
          className={styles.sendButton}
          style={{
            backgroundColor: choice.length === 0 ? "#3C3C43" : "#FFB930",
            color: choice.length === 0 ? "#ACACAC" : "#282828",
            cursor: choice.length === 0 ? "default" : "pointer",
          }}
          onClick={() =>
            {
              if (choice !== '') {
                let isCustomMessage = false;
                if (Object.keys(options).length > 0) {
                  isCustomMessage = Object.values(options).includes(choice);
                }
                if (
                  selectedOption &&
                  Object.values(selectedOption).length > 0
                ) {
                  isCustomMessage =
                    !(isCustomMessage ||
                    Object.values(selectedOption).includes(choice))
                }

                handleSend(
                  setShowChoicesSection,
                  setSelectedOption,
                  setOptions,
                  isCustomMessage
                );
              }
            }
          }
        >
          Send
        </div>
      </div>
    </div>
  );
};

export default Input;

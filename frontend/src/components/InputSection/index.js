import { useState, useRef, useEffect } from "react";

import TextareaAutosize from "./textareaAutosize.js";
import ChoicesSection from "./choice.js";

import styles from "./index.module.css";

const Input = ({
  showChoices,
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
  const [showChoicesSection, setShowChoicesSection] = useState(false);
  const [disableInput, setDisableInput] = useState(false);

  useEffect(() => {
    setShowChoicesSection(showChoices);
  }, [showChoices]);

  useEffect(() => {
    if (Object.keys(options).length === 0) {
      setDisableInput(!allowCustomInput);
    }
  }, [options, allowCustomInput]);

  const divRef = useRef(null);

  const handleMessageChange = (e) => {
    (allowCustomInput && !disableInput) && setChoice(e.target.value);
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

  const handleClickSend = () => {
    if (choice !== "") {
      let isAnyOptions = false;

      if (options && Object.keys(options).length > 0) {
        if (typeof options === "string") {
          isAnyOptions = options === choice;
        } else {
          isAnyOptions = Object.values(options).includes(choice);
        }
      }

      if (selectedOption && Object.values(selectedOption).length > 0) {
        if (typeof selectedOption === "string") {
          isAnyOptions = isAnyOptions && selectedOption === choice;
        } else {
          isAnyOptions =
            isAnyOptions || Object.values(selectedOption).includes(choice);
        }
      }

      if (!showChoicesSection) {
        isAnyOptions = true;
      }

      handleSend(
        setShowChoicesSection,
        setSelectedOption,
        setOptions,
        !isAnyOptions,
        setDisableInput
      );
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
          onClick={handleClickSend}
        >
          Send
        </div>
      </div>
    </div>
  );
};

export default Input;

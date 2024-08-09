import { Post } from "../../../utils/request";

function handleSend(
  chatHistory,
  setChatHistory,
  setShowProgress,
  choice,
  setChoice,
  selectedButton,
  setSelectedButton,
  conversationID,
  setShowConfetti
) {
  return function (
    setShowChoicesSection,
    setSelectedOption,
    setOptions,
    isCustomInput,
    setDisableInput
  ) {
    send(
      chatHistory,
      setChatHistory,
      setShowProgress,
      setShowChoicesSection,
      choice,
      setChoice,
      selectedButton,
      setSelectedButton,
      setSelectedOption,
      setOptions,
      conversationID,
      isCustomInput,
      setDisableInput,
      setShowConfetti
    );
  };
}

async function send(
  chatHistory,
  setChatHistory,
  setShowProgress,
  setShowChoicesSection,
  choice,
  setChoice,
  selectedButton,
  setSelectedButton,
  setSelectedOption,
  setOptions,
  conversationID,
  isCustomInput,
  setDisableInput,
  setShowConfetti
) {
  const fetchData = async () => {
    const body = () => {
      if (isCustomInput) {
        return {
          option: "custom",
          message: choice,
        };
      }
      return {
        option: "index",
        index: parseInt(selectedButton),
      };
    };

    const next = await Post(`conversations/${conversationID}/next`, body());
    return next;
  };

  const fetchNextMove = async () => {
    const next = await Post(`conversations/${conversationID}/next`, {
      option: "none",
    });
    return next;
  };

  const feedbackWithNoFollowUpFollowedByNP = (
    nextFetched,
    selectionResultContent
  ) => {
    // feedback would always not have follow_up
    console.log("feedbackWithNoFollowUpFollowedByNP");
    setOptions(Object.assign({}, nextFetched.options));
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
    const nextFetchedContent2 = await fetchNextMove();
    setOptions(Object.assign({}, nextFetchedContent2.data.options));
    setShowChoicesSection(true);

    return [
      returnFeedback(selectionResultContent),
      {
        type: "text",
        isSentByUser: false,
        content: nextFetched.content,
      },
    ];
  };

  async function handleContinue(
    oldHistory,
    selectionResultContent,
    setShowProgress
  ) {
    console.log("handleContinue");
    setShowProgress(true);
    const nextFetched2 = await fetchNextMove();
    setShowProgress(false);

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
  }

  const apFollowedByFeedback = async (
    nextFetched,
    oldHistory,
    selectionResultContent
  ) => {
    // ap followed by feedback with no follow_up
    if (!nextFetched.content.follow_up) {
      console.log("apFollowedByFeedback", selectionResultContent, nextFetched);
      setChoice(nextFetched.content.follow_up);
      setOptions({ 0: nextFetched.content.follow_up });
      setSelectedButton(0);
      setSelectedOption(0);
      return [
        ...oldHistory,
        {
          type: "text",
          isSentByUser: false,
          content: selectionResultContent,
        },
        returnFeedback(
          nextFetched.content,
          selectionResultContent,
          handleContinue
        ),
      ];
    } else {
      console.log("apFollowedByFeedbackWithFollowUp", nextFetched);
      setChoice(nextFetched.content.follow_up);
      setOptions({ 0: nextFetched.content.follow_up });
      setSelectedButton(0);
      setSelectedOption(0);
      return [
        ...oldHistory,
        {
          type: "text",
          isSentByUser: false,
          content: selectionResultContent,
        },
        returnFeedback(nextFetched.content),
      ];
    }
  };

  const handleContinueOnFeedbackWithNoFollowUp = async (
    oldHistory,
    selectionResultContent
  ) => {
    console.log("handleContinueOnFeedbackWithNoFollowUp");
    setShowProgress(true);
    const nextFetched = await fetchNextMove();
    setShowProgress(false);

    if (nextFetched.data.type === "ap") {
      setChatHistory([
        ...oldHistory,
        returnFeedback(selectionResultContent),
        {
          type: "typingIndicator",
          isSentByUser: false,
        },
      ]);

      setChatHistory([
        ...oldHistory,
        ...(await feedbackWithNoFollowUpFollowedByApAndNp(
          selectionResultContent,
          nextFetched.data
        )),
      ]);
    } else {
      console.log("2 handleContinueOnFeedbackWithNoFollowUp");
      const nextFetched = await fetchNextMove();

      setChatHistory([
        ...oldHistory,
        ...(await feedbackWithNoFollowUpFollowedByNP(
          nextFetched.data,
          oldHistory
        )),
      ]);
    }
  };

  const returnNewHistory = async (
    oldHistory,
    selectionResultType,
    selectionResultContent
  ) => {
    if (
      selectionResultType === "feedback" &&
      selectionResultContent?.follow_up
    ) {
      console.log("1");
      setOptions({ 0: selectionResultContent.follow_up });
      setChoice(selectionResultContent.follow_up);
      setSelectedButton(0);
      setSelectedOption(0);
      return [...oldHistory, returnFeedback(selectionResultContent)];
    }

    // if the first call fetched feedback with no follow up
    if (selectionResultType === "feedback") {
      console.log("232");
      return [
        ...oldHistory,
        returnFeedback(
          selectionResultContent,
          selectionResultContent,
          handleContinueOnFeedbackWithNoFollowUp
        ),
      ];
    }

    const nextFetched = await fetchNextMove();

    if (selectionResultType === "ap") {
      if (nextFetched.data.type === "feedback") {
        console.log("??");
        return await apFollowedByFeedback(
          nextFetched.data,
          oldHistory,
          selectionResultContent
        );
      } else if (nextFetched.data.type === "np") {
        console.log("4", selectionResultContent);
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

  setDisableInput(true);

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

  const returnFeedback = (content, continueContent, handleClick) => {
    const feedback = {
      type: "feedback",
      content: {
        body: content.body,
        choice: content.follow_up,
        title: content.title,
      },
    };

    if (continueContent) {
      feedback["continue"] = {
        handleClick: handleClick,
        oldHistory: oldHistory,
        selectionResultContent: continueContent,
      };
    }

    return feedback;
  };

  const max_level_unlocked_copy = localStorage.getItem("max_unlocked_stage");

  setChoice("");
  setSelectedOption(null);
  setShowChoicesSection(false);
  setShowProgress(true);
  setChatHistory(oldHistory);

  const selectionResult = await fetchData();
  const max_unlocked_stage = selectionResult.data.max_unlocked_stage;

  if (max_level_unlocked_copy !== max_unlocked_stage) {
    let unlockedLevel = 'Playground';
    if (max_unlocked_stage === 'level-1') {
      unlockedLevel = 'Level 2';
    }
    setShowConfetti([true, `Congratulations! You unlocked ${unlockedLevel}!`]);
  }

  localStorage.setItem("max_unlocked_stage", max_unlocked_stage);

  setShowProgress(false);

  if (!selectionResult.ok) {
    console.log("error");
    return;
  }
  const selectionResultType = selectionResult.data.type;

  if (selectionResultType !== "feedback") {
    setChatHistory(oldHistoryWithIndicator);
  }

  const newChatHistory = await returnNewHistory(
    oldHistory,
    selectionResultType,
    selectionResult.data?.content
  );

  setDisableInput(false);
  setChatHistory(newChatHistory);
}

export default handleSend;

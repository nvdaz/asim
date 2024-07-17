import { Post } from "../../../utils/request";

function handleSend(
  chatHistory,
  setChatHistory,
  setShowProgress,
  choice,
  setChoice,
  selectedButton,
  setSelectedButton,
  conversationID
) {
  return function (setShowChoicesSection, setSelectedOption, setOptions, isCustomInput) {
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
      isCustomInput
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
  isCustomInput
) {
  const fetchData = async (option = null) => {
    const body = () => {
      if (option === null) {
        return { option: "none" };
      }

      if (isCustomInput) {
        return {
          option: "custom",
          message: choice,
        };
      }
      return {
        option: isCustomInput ? "custom" : "index",
        index: parseInt(option),
      };
    }

    const next = await Post(`conversations/${conversationID}/next`, body());
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
    const nextFetchedContent2 = await fetchData();
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
    setShowProgress(true);
    const nextFetched2 = await fetchData();
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
      setSelectedButton(0);
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
      setSelectedButton(0);
      return [
        ...oldHistory,
        {
          type: "text",
          isSentByUser: false,
          content: selectionResultContent,
        },
        returnFeedback(nextFetched.content)
      ];
    }
  };

  const handleContinueOnFeedbackWithNoFollowUp = async (
    oldHistory,
    selectionResultContent
  ) => {
    console.log("handleContinueOnFeedbackWithNoFollowUp");
    setShowProgress(true);
    const nextFetched = await fetchData();
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
      const nextFetched = await fetchData();

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
      setChoice(selectionResultContent.follow_up);
      setSelectedButton(0);
      return [
        ...oldHistory,
        returnFeedback(selectionResultContent)
      ];
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

    const nextFetched = await fetchData();

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

  const resetStates = () => {
    setShowChoicesSection(false);
    setChoice("");
    setSelectedButton(null);
    setSelectedOption(null);
    setShowProgress(true);
  };

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
        handleClick: handleContinueOnFeedbackWithNoFollowUp,
        oldHistory: oldHistory,
        selectionResultContent: continueContent,
      };
    }

    return feedback;
  };

  resetStates();
  setChatHistory(oldHistory);

  const selectionResult = await fetchData(selectedButton);
  setShowProgress(false);

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
}

export default handleSend;

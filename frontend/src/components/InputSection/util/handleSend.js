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
  return function (setShowChoicesSection, setSelectedOption, setOptions) {
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
      conversationID
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
  conversationID
) {
  const fetchData = async (option = selectedButton) => {
    const next = await Post(`conversations/${conversationID}/next`, {
      option: "index",
      index: parseInt(option),
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
    const nextFetchedContent2 = await fetchData();
    setOptions(Object.assign({}, nextFetchedContent2.data.options));
    setShowChoicesSection(true);

    return [
      {
        type: "feedback",
        content: {
          body: selectionResultContent.body,
          choice: selectionResultContent.follow_up,
          title: selectionResultContent.title,
        },
      },
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
      selectedButton(0);
      return [
        ...oldHistory,
        {
          type: "text",
          isSentByUser: false,
          content: selectionResultContent,
        },
        {
          type: "feedback",
          content: {
            body: nextFetched.content.body,
            choice: nextFetched.content.follow_up,
            title: nextFetched.content.title,
          },
          continue: {
            handleClick: handleContinue,
            oldHistory: oldHistory,
            selectionResultContent: selectionResultContent,
          },
        },
      ];
    } else {
      console.log("apFollowedByFeedbackWithFollowUp", nextFetched);
      setChoice(nextFetched.content.follow_up);
      selectedButton(0);
      return [
        ...oldHistory,
        {
          type: "text",
          isSentByUser: false,
          content: selectionResultContent,
        },
        {
          type: "feedback",
          content: {
            body: nextFetched.content.body,
            choice: nextFetched.content.follow_up,
            title: nextFetched.content.title,
          },
        },
      ];
    }
  };

  const handleContinueOnFeedbackWithNoFollowUp = async (
    oldHistory,
    selectionResultContent
  ) => {
    setShowProgress(true);
    const nextFetched = await fetchData();
    setShowProgress(false);

    if (nextFetched.data.type === "ap") {
      setChatHistory([
        ...oldHistory,
        {
          type: "feedback",
          content: {
            body: selectionResultContent.body,
            title: selectionResultContent.title,
          },
        },
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
      selectedButton(0);
      return [
        ...oldHistory,
        {
          type: "feedback",
          content: {
            body: selectionResultContent.body,
            choice: selectionResultContent.follow_up,
            title: selectionResultContent.title,
          },
        },
      ];
    }

    // if the first call fetched feedback with no follow up
    if (selectionResultType === "feedback") {
      console.log("232");
      return [
        ...oldHistory,
        {
          type: "feedback",
          content: {
            body: selectionResultContent.body,
            title: selectionResultContent.title,
          },
          continue: {
            handleClick: handleContinueOnFeedbackWithNoFollowUp,
            oldHistory: oldHistory,
            selectionResultContent: selectionResultContent,
          },
        },
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

  resetStates();
  setChatHistory(oldHistory);

  const selectionResult = await fetchData();
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

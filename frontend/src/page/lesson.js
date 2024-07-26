import { useState, useCallback, useEffect } from "react";
import { useParams } from "react-router-dom";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import CelebrationIcon from "@mui/icons-material/Celebration";
import LockIcon from "@mui/icons-material/Lock";
import Confetti from "react-confetti";

import Header from "../components/header/index.js";
import InputAndMessages from "../components/InputAndMessages/index.js";
import { Post, Get } from "../utils/request";

import styles from "./page.module.css";

const Lesson = () => {
  const { conversationIDFromParam } = useParams();
  const [headerHeight, setHeaderHeight] = useState(null);
  const [data, setData] = useState(null);
  const [conversationList, setConversationList] = useState(null);
  const [nextConversation, setNextConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showConfetti, setShowConfetti] = useState([false, undefined]);
  const [alertMessage, setAlertMessage] = useState("");
  const currentLevel = window.location.href.split("/")[4] - 1;
  const max_unlocked_stage = localStorage.getItem("max_unlocked_stage");

  useEffect(() => {
    if (max_unlocked_stage !== `level-${currentLevel}`) {
      setTimeout(() => {
        window.location.href = `/`;
      }, 2000);
    }
  }, [max_unlocked_stage, currentLevel]);

  const fetchNextSteps = async (conversationID, condition) => {
    const next = await Post(`conversations/${conversationID}/next`, {
      option: "none",
    });
    if (!next.ok) {
      setAlertMessage("Error occurred fetching data");
      return;
    }

    if (condition || next.data.type === "ap") {
      const userOptions = await Post(`conversations/${conversationID}/next`, {
        option: "none",
      });
      if (!userOptions.ok) {
        setAlertMessage("Error occurred fetching data");
        return;
      }

      console.log("fetchNextSteps 1", {
        options: userOptions.data.options,
        ap_message: next.data.content,
      });
    } else {
      console.log("fetchNextSteps 2", next.data);
      setNextConversation(next.data);
    }
  };

  const fetchNewConversation = useCallback(async () => {
    const initConversation = await Post("conversations/", {
      type: "level",
      level: currentLevel,
    });
    if (!initConversation.ok) {
      setAlertMessage("Error occurred fetching data");
      return;
    }

    await fetchNextSteps(
      initConversation.data.id,
      !initConversation.data.info.scenario.is_user_initiated
    );
  }, [currentLevel]);

  useEffect(() => {
    const fetchData = async () => {
      if (typeof currentLevel !== "number") {
        setAlertMessage("Invalid url parameter");
      }

      const listConversations = await Get(
        `conversations/?type=level&level=${currentLevel}`
      );
      if (!listConversations.ok) {
        setAlertMessage("Error occurred fetching data");
        return;
      }

      setConversationList(listConversations.data);

      if (listConversations.data.length === 0) {
        await fetchNewConversation();
      } else {
        const conversationID =
          conversationIDFromParam ||
          listConversations.data[listConversations.data.length - 1].id;

        console.log(conversationIDFromParam, conversationID);
        const history = await Get(`conversations/${conversationID}`);
        if (!history.ok) {
          setAlertMessage("Error occurred fetching data");
          return;
        }
        const historyData = history.data;

        setData({
          id: conversationID,
          subject_name: historyData.agent,
          scenario: historyData.info.scenario,
          messages: historyData.elements,
        });

        if (historyData.state === null) {
          await fetchNextSteps(conversationID);
        } else if (historyData.state.waiting) {
          console.log("historyData.state.waiting", historyData.state.waiting);

          if (historyData.elements.length === 0) {
            setNextConversation({
              options: historyData.state.options,
            });
          } else {
            setNextConversation({
              options:
                historyData.elements[historyData.elements.length - 1].type !==
                "feedback"
                  ? historyData.state.options
                  : [],
            });
          }
        } else {
          await fetchNextSteps(conversationID);
        }
      }

      setLoading(false);
    };

    fetchData();
  }, [conversationIDFromParam, currentLevel, fetchNewConversation]);

  const header = useCallback((node) => {
    if (node !== null) {
      setHeaderHeight(node.getBoundingClientRect().height);
    }
  }, []);

  const alert = (severity, icon) => {
    return (
      <Collapse in={showConfetti[0] || alertMessage !== ""} sx={{ zIndex: 3 }}>
        <Alert
          icon={icon}
          action={
            <IconButton
              aria-label="close"
              color="inherit"
              size="small"
              onClick={() => {
                setAlertMessage(null);
                setShowConfetti([false, undefined]);
              }}
            >
              <CloseIcon fontSize="inherit" />
            </IconButton>
          }
          sx={{ position: "absolute", top: "20px", right: "20px", zIndex: 3 }}
          variant="filled"
          severity={severity}
        >
          {showConfetti[1] || alertMessage}
        </Alert>
      </Collapse>
    );
  };

  const lesson = () => {
    return (
      <div className={styles.wrapper}>
        {alertMessage && alert("warning")}
        {loading ? (
          <div className={styles.initLesson}>
            <CircularProgress />
            <div style={{ color: "white" }}>Initializing Lesson</div>
          </div>
        ) : (
          <div style={{ width: "100%", height: "100%" }}>
            {showConfetti[0] && (
              <div>
                <Confetti />
                {alert("success", <CelebrationIcon />)}
              </div>
            )}
            <div ref={header}>
              <Header
                name={data?.["subject_name"]}
                initData={{
                  scenario: data?.["scenario"]?.["user_perspective"],
                  goal: data?.["scenario"]?.["user_goal"],
                }}
                fetchNewConversation={fetchNewConversation}
                conversationList={conversationList}
                currentLevel={currentLevel}
              />
            </div>
            <InputAndMessages
              subjectName={data?.["subject_name"]}
              explanationText={"Choose the best option:"}
              inputPlaceholder={"Choose the best option to send"}
              headerHeight={headerHeight}
              setShowConfetti={setShowConfetti}
              initData={{
                id: data?.id,
                options: nextConversation?.options,
                is_user_initiated: data?.scenario?.is_user_initiated,
                ap_message: nextConversation?.ap_message,
                messages: data?.messages || [],
              }}
            />
          </div>
        )}
      </div>
    );

  }

  return (
    <div className={styles.wrapper}>
      {max_unlocked_stage !== `level-${currentLevel}` ? (
        <div className={styles.unavailableWrapper}>
          <div className={styles.unavailableTitle}>Lesson 2 Locked<LockIcon/></div>
          <div>Send 8 messages in Lesson 1 to unlock</div>
          <div>Going back to main page...</div>
          <div>
            Click{" "}
            <a
              href="/"
              style={{ color: "turquoise", textDecoration: "underline" }}
            >
              here
            </a>{" "}
            if nothing is happening
          </div>
        </div>
      ) : (
        lesson()
      )}
    </div>
  );
};

export default Lesson;

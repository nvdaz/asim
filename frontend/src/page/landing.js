import { useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import useMediaQuery from "@mui/material/useMediaQuery";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";
import ClickAwayListener from "@mui/material/ClickAwayListener";

import TextareaAutosize from "../components/InputSection/textareaAutosize";
import { Post } from "../utils/request";

import styles from "./page.module.css";

const Landing = () => {
  const { magicLink } = useParams();
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(true);
  const [enteredName, setEnteredName] = useState("");
  const [alertMessage, setAlertMessage] = useState("");
  const [mode, selectedMode] = useState("Learn");
  const isMobile = useMediaQuery("(max-width:600px)");
  const allowedLessons = localStorage.getItem("max_unlocked_stage");
  const [open, setOpen] = useState(false);
  const [open2, setOpen2] = useState(false);
  const [playgroundOpen, setPlaygroundOpen] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem("token");

      if (!token) {
        if (!magicLink) {
          setAlertMessage("Please use sign-up link");
          return;
        }
        const res2 = await Post("auth/exchange", {
          magic_link: magicLink,
        });
        if (!res2.ok) {
          setAlertMessage("Error occurred");
          return;
        }
        localStorage.setItem("token", res2.data.token);
        localStorage.setItem("init", res2.data.user.init);
        localStorage.setItem(
          "max_unlocked_stage",
          res2.data.user.max_unlocked_stage
        );

        if (!res2.data.user.init) {
          setFetching(false);
          return;
        }
      }
      if (localStorage.getItem("init") === null) {
        setFetching(false);
        return;
      }
      setLoading(false);
    };

    fetchData();
  }, [magicLink]);

  const handleMessageChange = (e) => {
    setEnteredName(e.target.value);
  };

  const handleSend = async (e) => {
    e.preventDefault();
    const setupName = await Post("auth/setup", {
      name: enteredName,
    });

    if (!setupName.ok) {
      setAlertMessage(
        "Submission failed. Please make sure your signup link is correct."
      );
      return;
    }

    localStorage.setItem("init", true);
    window.location.href = "/";
  };

  const loginAndInitSetUp = () => {
    return fetching ? (
      <div className={styles.loadingWrapper}>
        <CircularProgress />
        <div style={{ color: "white" }}>Loading</div>
      </div>
    ) : (
      <div className={styles.setUpWrapper}>
        <div>Welcome! What is your name?</div>
        <div>
          It will be how you are addressed during conversations and when given
          feedback.
        </div>
        <div className={styles.textAreaWrapper}>
          <div style={{ width: "40%" }}>
            {Boolean(enteredName) && (
              <div style={{ padding: "15px 0 20px 0" }}>Hi {enteredName}!</div>
            )}
            <TextareaAutosize
              value={enteredName}
              onChange={handleMessageChange}
            />
          </div>
        </div>
        <div className={styles.btnWrapper}>
          <div
            style={{
              backgroundColor: Boolean(enteredName) ? "#FFB930" : "#3C3C43",
              color: Boolean(enteredName) ? "#282828" : "#ACACAC",
              cursor: Boolean(enteredName) ? "pointer" : "default",
            }}
            onClick={handleSend}
          >
            Send
          </div>
        </div>
      </div>
    );
  };

  const lessonsSection = () => {
    return (
      <div>
        <div
          className={styles.columnRightBtnWrapper}
          style={{ marginRight: "100px" }}
        >
          Lesson 1
          <div style={{ marginBottom: "10px" }}>Ambiguous Questions</div>
          <Button
            sx={{
              backgroundColor: "#FFB930",
              textTransform: "none",
              borderRadius: "50%",
              padding: 0,
              "&:hover": {
                backgroundColor: "#FF9430",
              },
              "& .MuiTouchRipple-child": {
                backgroundColor: "#FFCC69",
              },
            }}
          >
            <div
              className={styles.lessonsBtn}
              onClick={() =>
                setTimeout(() => {
                  window.location.href = "/lesson/1";
                }, "250")
              }
            >
              {allowedLessons === "level-1" && "Start"}
            </div>
          </Button>
        </div>
        <div
          className={styles.columnRightBtnWrapper}
          style={{ marginLeft: "100px" }}
        >
          Lesson 2<div style={{ marginBottom: "10px" }}>Ambiguous Answers</div>
          <ClickAwayListener onClickAway={() => setOpen(false)}>
            <Tooltip
              PopperProps={{
                disablePortal: true,
              }}
              onClose={() => setOpen(false)}
              open={open}
              disableFocusListener
              disableHoverListener
              disableTouchListener
              title="Send 8 messages in Level 1 to unlock!"
              arrow
            >
              <Button
                sx={{
                  backgroundColor:
                    allowedLessons >= "level-2" ||
                    allowedLessons === "playground"
                      ? "#FFB930"
                      : "#797979",
                  textTransform: "none",
                  borderRadius: "50%",
                  padding: 0,
                  "&:hover": {
                    backgroundColor:
                      allowedLessons >= "level-2" ||
                      allowedLessons === "playground"
                        ? "#FF9430"
                        : "##A3A3A3",
                  },
                  "& .MuiTouchRipple-child": {
                    backgroundColor:
                      allowedLessons >= "level-2" ||
                      allowedLessons === "playground"
                        ? "#FFCC69"
                        : "#637BC4",
                  },
                }}
              >
                <div
                  className={styles.lessonsBtn}
                  onClick={() => {
                    if (
                      allowedLessons >= "level-2" ||
                      allowedLessons >= "playground"
                    ) {
                      setTimeout(() => {
                        window.location.href = "/lesson/2";
                      }, "250");
                    } else {
                      setOpen(true);
                    }
                  }}
                >
                  {allowedLessons === "level-2" && "Start"}
                </div>
              </Button>
            </Tooltip>
          </ClickAwayListener>
        </div>
        <div
          className={styles.columnRightBtnWrapper}
          style={{ marginRight: "100px" }}
        >
          Lesson 3
          <div style={{ marginBottom: "10px" }}>Frustrating Situation</div>
          <ClickAwayListener
            onClickAway={() => {
              setOpen2(false);
              console.log("--");
            }}
          >
            <Tooltip
              PopperProps={{
                disablePortal: true,
              }}
              onClose={() => {
                setOpen2(false);
                console.log("--");
              }}
              open={open2}
              disableFocusListener
              disableHoverListener
              disableTouchListener
              title="Send 8 messages in Level 2 to unlock!"
              arrow
            >
              <Button
                sx={{
                  backgroundColor:
                    allowedLessons >= "level-3" ||
                    allowedLessons === "playground"
                      ? "#FFB930"
                      : "#797979",
                  textTransform: "none",
                  borderRadius: "50%",
                  padding: 0,
                  "&:hover": {
                    backgroundColor:
                      allowedLessons >= "level-3" ||
                      allowedLessons === "playground"
                        ? "#FF9430"
                        : "##A3A3A3",
                  },
                  "& .MuiTouchRipple-child": {
                    backgroundColor:
                      allowedLessons >= "level-3" ||
                      allowedLessons === "playground"
                        ? "#FFCC69"
                        : "#637BC4",
                  },
                }}
              >
                <div
                  className={styles.lessonsBtn}
                  onClick={() => {
                    if (
                      allowedLessons >= "level-3" ||
                      allowedLessons === "playground"
                    ) {
                      setTimeout(() => {
                        window.location.href = "/lesson/3";
                      }, "250");
                    } else {
                      setOpen2(true);
                    }
                  }}
                >
                  {allowedLessons === "level-3" && "Start"}
                </div>
              </Button>
            </Tooltip>
          </ClickAwayListener>
        </div>
      </div>
    );
  };

  const btn = (name) => {
    let style;
    if (mode !== name) {
      style =
        name === "Playground"
          ? { marginRight: "20px" }
          : { marginLeft: "20px" };
    }

    return (
      <div
        className={mode === name ? styles.btnSelected : styles.btn}
        style={style}
        onClick={() => {
          if (name === "Playground") {
            if (allowedLessons === "playground") {
              selectedMode(name);
              setTimeout(() => {
                window.location.href = "/playground";
              }, "250");
            }
            else {
              setPlaygroundOpen(true);
              return;
            }
          }
          selectedMode(name);
        }}
      >
        {name}
      </div>
    );
  };

  const playgroundBtn = () => {
    return (
      <ClickAwayListener onClickAway={() => setPlaygroundOpen(false)}>
        <Tooltip
          placement="bottom-start"
          PopperProps={{
            disablePortal: true,
          }}
          onClose={() => setPlaygroundOpen(false)}
          open={playgroundOpen}
          disableFocusListener
          disableHoverListener
          disableTouchListener
          title="Send 8 messages in each lesson to unlock!"
          arrow
        >
          {btn("Playground")}
        </Tooltip>
      </ClickAwayListener>
    );
  }

  const landingPage = () => {
    return isMobile ? (
      <div style={{ height: "100%", width: "100%", margin: "16px" }}>
        <div className={styles.columnRightMobile}>{lessonsSection()}</div>
        <div className={styles.mobileBtnWrapper}>
          {btn("Learn")}
          {playgroundBtn()}
        </div>
      </div>
    ) : (
      <div className={styles.wrapper}>
        <div className={styles.column}>
          <div style={{ padding: "3rem 2rem" }}>
            {btn("Learn")}
            {playgroundBtn()}
          </div>
        </div>
        <div className={styles.columnRight}>{lessonsSection()}</div>
      </div>
    );
  };

  return (
    <div className={styles.wrapper}>
      {alertMessage && (
        <Collapse in={alertMessage !== ""}>
          <Alert
            action={
              <IconButton
                aria-label="close"
                color="inherit"
                size="small"
                onClick={() => {
                  setAlertMessage(null);
                }}
              >
                <CloseIcon fontSize="inherit" />
              </IconButton>
            }
            sx={{ position: "absolute", top: "20px" }}
            variant="filled"
            severity="warning"
          >
            {alertMessage}
          </Alert>
        </Collapse>
      )}
      {loading ? loginAndInitSetUp() : landingPage()}
    </div>
  );
};

export default Landing;

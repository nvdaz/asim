import { useState, useCallback } from "react";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import Avatar from "@mui/material/Avatar";
import CachedIcon from "@mui/icons-material/Cached";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import PreviewIcon from "@mui/icons-material/Preview";
import FormatListNumberedIcon from "@mui/icons-material/FormatListNumbered";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import Tooltip from "@mui/material/Tooltip";

import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import Divider from "@mui/material/Divider";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";

import Dialog from "./dialog";
import { Link } from "react-router-dom";

import pic from "../../assets/jimmy.png";
import styles from "./header.module.css";

export default function Header({
  name,
  initData,
  fetchNewConversation,
  conversationList,
  currentLevel,
  showMore = true,
}) {
  const [gettingNewConversation, setGettingNewConversation] = useState(false);
  const [openDrawer, setOpenDrawer] = useState(true);
  const [openDialog, setOpenDialog] = useState(true);
  const [headerHeight, setHeaderHeight] = useState(null);
  const [showConversationList, setShowConversationList] = useState(false);

  const header = useCallback((node) => {
    if (node !== null) {
      setHeaderHeight(node.getBoundingClientRect().height);
    }
  }, []);

  const rightSideContent = () => {
    if (!showMore) {
      return <div>Topic: {initData.topic}</div>;
    }
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          gap: "20px",
          alignItems: "center",
        }}
      >
        <MoreHorizIcon
          onClick={() => setOpenDrawer(true)}
          style={{ cursor: "pointer" }}
        />

        <Dialog open={openDialog} setOpen={setOpenDialog} initData={initData} />

        <Drawer
          anchor={"right"}
          open={openDrawer}
          onClose={() => setOpenDrawer(false)}
        >
          <Box
            sx={{
              width: 250,
              maxHeight: "100%",
              backgroundColor: "rgb(30, 30, 30)",
              color: "white",
            }}
            role="presentation"
          >
            <List>
              <div ref={header}>
                <ListItem key={"scenario"} disablePadding>
                  <ListItemButton onClick={() => setOpenDialog(true)}>
                    <ListItemIcon>
                      <PreviewIcon
                        style={{ cursor: "pointer", color: "white" }}
                      />
                    </ListItemIcon>
                    <ListItemText primary={"View Scenario and Goal"} />
                  </ListItemButton>
                </ListItem>
                <Divider />
                <ListItem key={"check"} disablePadding>
                  <ListItemButton
                    onClick={() =>
                      setShowConversationList(!showConversationList)
                    }
                  >
                    <ListItemIcon>
                      <FormatListNumberedIcon
                        style={{ cursor: "pointer", color: "white" }}
                      />
                    </ListItemIcon>
                    <ListItemText primary={"Show past conversations"} />
                    <KeyboardArrowDownIcon
                      className={
                        showConversationList ? styles.arrowRotate : styles.arrow
                      }
                    />
                  </ListItemButton>
                </ListItem>
                {conversationList.length > 0 && <Divider />}
              </div>

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  height: `calc(100vh - ${headerHeight}px - 16px)`,
                }}
              >
                <div
                  style={{
                    overflowY: "auto",
                    backgroundColor: showConversationList
                      ? "#3F3F3F"
                      : "#1E1E1E",
                    flex: 1,
                  }}
                >
                  {showConversationList &&
                    conversationList.map((c, index) => (
                      <ListItem key={index} disablePadding>
                        <ListItemButton
                          style={{
                            paddingTop: index === 0 ? "10px" : "8px",
                            cursor: "default",
                          }}
                        >
                          <Tooltip title="Open conversation">
                            <ListItemIcon
                              style={{
                                paddingLeft: "20px",
                                color: "white",
                              }}
                            >
                              <OpenInNewIcon
                                sx={{ cursor: "pointer" }}
                                fontSize="small"
                                onClick={() =>
                                  (window.location.href = `/lesson/${currentLevel + 1}/${c.id}`)
                                }
                              />
                            </ListItemIcon>
                          </Tooltip>
                          <div key={index}>
                            {index + 1}. {c.agent}
                          </div>
                        </ListItemButton>
                      </ListItem>
                    ))}
                </div>

                <ListItem key={"getNew"} disablePadding>
                  <ListItemButton
                    sx={{
                      padding: "25px 15px",
                    }}
                    onClick={async () => {
                      setGettingNewConversation(true);
                      await fetchNewConversation();
                      window.location.href = `/lesson/${currentLevel + 1}`;
                    }}
                  >
                    <ListItemIcon>
                      <CachedIcon
                        className={
                          gettingNewConversation ? styles.rotate : styles.none
                        }
                        sx={{ color: "#FF9300", cursor: "pointer" }}
                      />
                    </ListItemIcon>
                    <ListItemText primary={"Get new conversation"} />
                  </ListItemButton>
                </ListItem>
              </div>
            </List>
          </Box>
        </Drawer>
      </div>
    );
  };

  return (
    <div
      style={{
        width: "100%",
        backgroundColor: "#292929",
        borderBottom: "#333333 1px solid",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "16px",
          color: "white",
          fontSize: "15px",
        }}
      >
        <Link style={{ color: "white" }} to="/">
          <ArrowBackIosNewIcon style={{ cursor: "pointer" }} />
        </Link>
        <div
          style={{
            display: "flex",
            gap: "10px",
            alignItems: "center",
          }}
        >
          <Avatar alt="Jimmy" sx={{ width: 35, height: 35 }} src={pic} />
          <div>{name}</div>
        </div>
        {rightSideContent()}
      </div>
    </div>
  );
}

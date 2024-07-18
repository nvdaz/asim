import * as React from "react";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";

import styles from "./header.module.css"

function SimpleDialog(props) {
  const { onClose, open, initData } = props;

  return (
    <Dialog
      PaperProps={{
        sx: {
          borderRadius: "24px",
          margin: "16px",
        },
      }}
      onClose={onClose}
      open={open}
    >
      <div className={styles.dialogContentWrapper}>
        <IconButton
          aria-label="close"
          onClick={onClose}
          size={"small"}
          sx={{
            position: "absolute",
            right: 4,
            top: 4,
            color: "black",
          }}
        >
          <CloseIcon />
        </IconButton>
        {initData.topic ? (
          <div
            style={{
              padding: "10px 15px 10px 8px",
            }}
          >
            <div
              style={{
                fontSize: "1.4rem",
                paddingBottom: "5px",
                fontWeight: 550,
              }}
            >
              Topic:
            </div>
            {initData.topic}
          </div>
        ) : (
          scenarioAndGoal(initData)
        )}
      </div>
    </Dialog>
  );
}

const scenarioAndGoal = (initData) => {
  return (
    <div>
      <div
        style={{
          paddingBottom: "5px",
        }}
      >
        <div
          style={{
            fontSize: "1.4rem",
            paddingBottom: "5px",
            fontWeight: 550,
          }}
        >
          Scenario:
        </div>
        {initData.scenario}
      </div>
      <hr />
      <div>
        <div
          style={{
            fontSize: "1.4rem",
            padding: "5px 0",
            fontWeight: 550,
          }}
        >
          Goal:
        </div>
        {initData.goal}
      </div>
    </div>
  );
};

SimpleDialog.propTypes = {
  onClose: PropTypes.func.isRequired,
  open: PropTypes.bool.isRequired,
};

export default function SimpleDialogDemo({ open, setOpen, initData }) {

  return (
    <SimpleDialog
      open={open}
      onClose={() => setOpen(false)}
      initData={initData}
    />
  );
}

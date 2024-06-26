import * as React from "react";
import PropTypes from "prop-types";
import Dialog from "@mui/material/Dialog";

const emails = ["username@gmail.com", "user02@gmail.com"];

function SimpleDialog(props) {
  const { onClose, selectedValue, open, initData } = props;

  const handleClose = () => {
    onClose(selectedValue);
  };

  return (
    <Dialog onClose={handleClose} open={open}>
      <div style={{ backgroundColor: "#B4B4B5", padding: "20px" }}>
        <div
          style={{
            paddingBottom: "15px",
          }}
        >
          <div
            style={{
              fontSize: "17px",
              paddingBottom: "5px",
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
              fontSize: "17px",
              padding: "5px 0",
            }}
          >
            Goal:
          </div>
          {initData.goal}
        </div>
      </div>
    </Dialog>
  );
}

SimpleDialog.propTypes = {
  onClose: PropTypes.func.isRequired,
  open: PropTypes.bool.isRequired,
  selectedValue: PropTypes.string.isRequired,
};

export default function SimpleDialogDemo({ initData }) {
  const [open, setOpen] = React.useState(true);
  const [selectedValue, setSelectedValue] = React.useState(emails[1]);

  const handleClickOpen = () => {
    setOpen(true);
  };

  const handleClose = (value) => {
    setOpen(false);
    setSelectedValue(value);
  };

  return (
    <div>
      <div style={{ cursor: "pointer" }} onClick={handleClickOpen}>
        Check Scenario and Goal
      </div>
      <SimpleDialog
        selectedValue={selectedValue}
        open={open}
        onClose={handleClose}
        initData={initData}
      />
    </div>
  );
}

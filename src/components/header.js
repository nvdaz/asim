import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import Avatar from "@mui/material/Avatar";
import pic from "../assets/jimmy.png";

export default function header() {
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
          fontSize: "12px",
        }}
      >
        <ArrowBackIosNewIcon style={{ cursor: "pointer" }} />
        <div
          style={{
            display: "flex",
            gap: "10px",
            alignItems: "center",
          }}
        >
          <Avatar
            alt="Jimmy"
            sx={{ width: 35, height: 35 }}
            src={pic}
          />
          <div>Jimmy</div>
        </div>
        <ArrowBackIosNewIcon style={{ opacity: 0 }} />
      </div>
    </div>
  );
}

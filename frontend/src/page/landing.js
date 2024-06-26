import { Link } from "react-router-dom";

const Landing = () => {
  return (
    <div className="wrapper">
      <Link style={{ color: "white" }} to="/lesson/1">
        Go to first lesson
      </Link>
      <Link style={{ color: "white" }} to="/lesson/2">
        Go to second lesson
      </Link>
    </div>
  );
};

export default Landing;

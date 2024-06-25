import { Link } from "react-router-dom";

const Landing = () => {
  return (
    <div className="wrapper">
      <Link to="/lesson">
        Go to first lesson
      </Link>
    </div>
  );
};

export default Landing;

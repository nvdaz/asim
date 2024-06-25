import { BrowserRouter, Route, Routes } from "react-router-dom";

import Lesson from "./page/lesson";
import Landing from "./page/landing";

function App() {

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/lesson" element={<Lesson />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

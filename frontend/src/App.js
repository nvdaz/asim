import { BrowserRouter, Route, Routes } from "react-router-dom";

import Lesson from "./page/lesson";
import Landing from "./page/landing";

import "./App.css";

function App() {

  return (
    <BrowserRouter>
      <Routes>
        <Route path={`/:uniqueString`} element={<Landing />} />
        <Route path={`/`} element={<Landing />} />
        <Route path="/lesson/1" element={<Lesson />} />
        <Route path="/lesson/2" element={<Lesson />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

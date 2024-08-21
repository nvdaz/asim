import { BrowserRouter, Route, Routes } from "react-router-dom";

import Landing from "./page/landing";
import Lesson from "./page/lesson";
import Playground from "./page/playground";

import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path={`/:magicLink`} element={<Landing />} />
        <Route path={`/`} element={<Landing />} />
        <Route
          path="/lesson/:lesson/:conversationIDFromParam?"
          element={<Lesson />}
        />
        <Route path="/playground" element={<Playground />} />
        <Route
          path="/playground/:conversationIDFromParam"
          element={<Playground />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

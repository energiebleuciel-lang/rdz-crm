import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import FormulaireSolaire from "./components/FormulaireSolaire";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<FormulaireSolaire />} />
        <Route path="*" element={<FormulaireSolaire />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

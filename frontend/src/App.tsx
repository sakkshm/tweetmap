import './App.css'
import { Route, Routes } from "react-router-dom"
import LandingPage from "./pages/LandingPage"
import HeatmapPage from "./pages/HeatmapPage"

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/heatmap/:username" element={<HeatmapPage />} />
    </Routes>
  )
}

export default App

import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/global.css";
import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
createRoot(document.getElementById("root")!).render(<React.StrictMode><BrowserRouter><App /></BrowserRouter></React.StrictMode>);

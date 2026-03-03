import { useState } from "react";
import MapView from "../components/Map/MapView";
import LeftPanel from "../components/LeftPanel/LeftPanel";
import RightPanel from "../components/RightPanel/RightPanel";
import Header from "../components/Header/Header";
import Footer from "../components/Footer/Footer";
import "./DashboardPage.css";

export default function DashboardPage() {
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);

    return (
        <div className={`dash ${rightOpen ? "right-open" : "right-closed"} ${leftOpen ? "left-open" : "left-closed"}`}>
          <MapView />

          <Header />
          <Footer />

          <LeftPanel open={leftOpen} onToggle={() => setLeftOpen((v) => !v)} />
          <RightPanel open={rightOpen} onToggle={() => setRightOpen((v) => !v)} />
        </div>
    );
}
import { BrowserRouter } from "react-router-dom";
import { Footer } from "./components/Footer";
import { Navbar } from "./components/Navbar";
import { AppRoutes } from "./pages";
import "./style.css";

export default function App() {
  return <BrowserRouter>
    <div className="site-frame">
      <Navbar />
      <main className="page-content"><AppRoutes /></main>
      <Footer />
    </div>
  </BrowserRouter>;
}

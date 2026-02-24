import "./Header.css";
import fireIcon from "../../assets/icons/fire.svg";

export default function Header() {
    return (
        <header className="appHeader">
            <div className="appHeaderTitleRow">
                <img className="appHeaderIcon" src={fireIcon} alt="" />
                <span className="appHeaderTitle">
                    Sistema de Análisis de Incendios Forestales en México
                </span>
            </div>
        </header>
    );
}
import "./Header.css";
import fireIcon from "../../assets/icons/fire.svg";

export default function Header() {
    return (
        <header className="appHeader">
            <div className="appHeaderTitleRow">
                <img className="appHeaderIcon" src={fireIcon} alt="" />
                <h1 className="appHeaderTitle">
                    Sistema de Análisis de Incendios Forestales en México
                </h1>
            </div>
        </header>
    );
}
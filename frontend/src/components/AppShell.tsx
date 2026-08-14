import { Link, NavLink, Outlet } from "react-router-dom";
import { useInjectedWallet } from "../hooks/useInjectedWallet";

const nav = [["/agreements", "Agreements"], ["/constitutions", "Constitutions"], ["/policies", "Policies"], ["/protocol", "Protocol"], ["/integration", "Integration"], ["/demo", "Demo"]] as const;

export function AppShell() {
  const wallet = useInjectedWallet();
  return <div className="app-shell">
    <a className="skip" href="#main">Skip to content</a>
    <header className="topbar"><Link className="brand" to="/"><span>L</span> LACUNA</Link><nav aria-label="Primary">{nav.map(([to, label]) => <NavLink key={to} to={to}>{label}</NavLink>)}</nav><div className="wallet-mini">{wallet.account ? <Link to="/account">{wallet.account.slice(0, 6)}…{wallet.account.slice(-4)}</Link> : <button onClick={() => void wallet.connect()}>Connect wallet</button>}</div></header>
    <main id="main"><Outlet /></main>
  </div>;
}

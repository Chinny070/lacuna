import { Link } from "react-router-dom";
import type { ReactNode } from "react";

export function PageHeader({ eyebrow, title, children, action }: { eyebrow: string; title: string; children?: ReactNode; action?: ReactNode }) { return <header className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1>{children && <div className="lede">{children}</div>}</div>{action}</header>; }
export function EmptyState({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) { return <section className="empty-state"><div className="orbital-mark">◌</div><h2>{title}</h2><p>{children}</p>{action}</section>; }
export function Loading() { return <p className="loading" aria-live="polite">Reading StudioNet state…</p>; }
export function ErrorNotice({ message }: { message: string }) { return <p className="error" role="alert">{message}</p>; }
export function Back({ to, children }: { to: string; children: ReactNode }) { return <Link className="back" to={to}>← {children}</Link>; }
export function Badge({ children }: { children: ReactNode }) { return <span className="badge">{children}</span>; }

"use client";

import Link from "next/link";
import { useState } from "react";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import {
  Activity,
  Bell,
  ChevronDown,
  CircleHelp,
  Database,
  Globe2,
  LayoutDashboard,
  Mail,
  Menu,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { LogoutButton } from "@/components/logout-button";

type DashboardShellProps = {
  email: string;
  children: ReactNode;
};

const upcomingItems = [
  { label: "Web Server", icon: Activity },
  { label: "Database", icon: Database },
  { label: "DNS", icon: Globe2 },
  { label: "SMTP", icon: Mail },
  { label: "Segurança", icon: ShieldCheck },
];

export function DashboardShell({ email, children }: DashboardShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  return (
    <div className="dashboard-shell">
      {mobileOpen && (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="Fechar menu"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside className={`sidebar${mobileOpen ? " sidebar-open" : ""}`} aria-label="Navegação principal">
        <div className="sidebar-brand-row">
          <Link href="/" className="sidebar-brand" aria-label="DevOps Monitor, visão geral">
            <BrandMark />
          </Link>
          <button
            className="icon-button sidebar-close"
            type="button"
            aria-label="Fechar navegação"
            onClick={() => setMobileOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <button className="workspace-switcher" type="button" disabled>
          <span className="workspace-mark">D</span>
          <span className="workspace-copy"><strong>Infraestrutura</strong><small>Ambiente de monitoramento</small></span>
          <ChevronDown size={15} aria-hidden="true" />
        </button>

        <nav className="side-navigation">
          <p className="nav-section-label">VISÃO GERAL</p>
          <Link className={`side-link${pathname === "/" ? " side-link-active" : ""}`} href="/" onClick={() => setMobileOpen(false)}>
            <LayoutDashboard size={17} aria-hidden="true" />
            <span>Visão geral</span>
          </Link>

          <p className="nav-section-label nav-section-spaced">MONITORAMENTO</p>
          {upcomingItems.slice(0, 4).map(({ label, icon: Icon }, index) => {
            const id = ["web", "db", "dns", "smtp"][index];
            return (
            <Link className={`side-link${pathname === `/services/${id}` ? " side-link-active" : ""}`} key={label} href={`/services/${id}`} onClick={() => setMobileOpen(false)}>
              <Icon size={17} aria-hidden="true" />
              <span>{label}</span>
            </Link>
          );})}

          <p className="nav-section-label nav-section-spaced">OPERAÇÕES</p>
          <Link className={`side-link${pathname === "/security" ? " side-link-active" : ""}`} href="/security" onClick={() => setMobileOpen(false)}>
            <ShieldCheck size={17} aria-hidden="true" />
            <span>Segurança</span>
          </Link>
          <div className="side-link side-link-disabled" aria-disabled="true" title="Disponível na próxima etapa">
            <Bell size={17} aria-hidden="true" />
            <span>Alertas</span>
            <span className="nav-upcoming">em breve</span>
          </div>
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-help"><CircleHelp size={16} /><span>Ajuda e documentação</span></div>
          <div className="sidebar-account">
            <span className="account-avatar">{email.charAt(0).toUpperCase()}</span>
            <span className="account-copy"><strong>Operador</strong><small title={email}>{email}</small></span>
            <LogoutButton />
          </div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <button
            className="icon-button mobile-menu-button"
            type="button"
            aria-label="Abrir navegação"
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen(true)}
          >
            <Menu size={19} />
          </button>
          <div className="breadcrumbs"><span>Workspace</span><b>/</b><strong>Visão geral</strong></div>
          <div className="topbar-actions">
            <span className="secure-session"><i /> Sessão autenticada</span>
            <button className="icon-button search-button" type="button" aria-label="Busca disponível em breve" disabled>
              <Search size={17} />
            </button>
            <button className="icon-button" type="button" aria-label="Notificações disponíveis em breve" disabled>
              <Bell size={17} />
            </button>
            <span className="topbar-avatar" aria-hidden="true">{email.charAt(0).toUpperCase()}</span>
          </div>
        </header>
        <main className="page-content">{children}</main>
        <footer className="page-footer">
          <span>DevOps Monitor <b>·</b> Plataforma de observabilidade</span>
          <span>Sessão protegida <i /></span>
        </footer>
      </div>
    </div>
  );
}

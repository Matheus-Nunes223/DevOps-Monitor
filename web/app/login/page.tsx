import type { Metadata } from "next";
import { Suspense } from "react";
import { Activity, ArrowUpRight, LockKeyhole, ShieldCheck, Waypoints } from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { LoginForm } from "@/components/login-form";
import { getSupabasePublicConfig } from "@/lib/supabase/config";

export const metadata: Metadata = {
  title: "Entrar",
  description: "Acesse o painel DevOps Monitor.",
};

type LoginPageProps = {
  searchParams: Promise<{ next?: string; reason?: string }>;
};

function getSafeRedirect(value?: string) {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return "/";
  }
  return value;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  const configured = Boolean(getSupabasePublicConfig());
  const safeRedirect = getSafeRedirect(params.next);

  return (
    <main className="login-page">
      <section className="login-visual" aria-label="Plataforma de monitoramento DevOps">
        <div className="visual-grid" aria-hidden="true" />
        <div className="visual-glow visual-glow-one" aria-hidden="true" />
        <div className="visual-glow visual-glow-two" aria-hidden="true" />
        <div className="visual-content">
          <BrandMark />
          <div className="visual-copy">
            <div className="eyebrow"><span /> OBSERVABILIDADE EM TEMPO REAL</div>
            <h1>Infraestrutura<br /><span>sob controle.</span></h1>
            <p>Uma visão clara da saúde dos seus serviços, alertas e eventos de segurança — em um único lugar.</p>
          </div>
          <div className="visual-diagram" aria-hidden="true">
            <div className="diagram-orbit orbit-one" /><div className="diagram-orbit orbit-two" />
            <div className="diagram-core"><Waypoints size={27} /></div>
            <div className="diagram-node node-web"><Activity size={17} /><i /></div>
            <div className="diagram-node node-db"><span className="database-glyph"><i /><i /><i /></span><i /></div>
            <div className="diagram-node node-dns"><span>DNS</span><i /></div>
            <div className="diagram-node node-smtp"><span>@</span><i /></div>
            <span className="diagram-line line-web" /><span className="diagram-line line-db" />
            <span className="diagram-line line-dns" /><span className="diagram-line line-smtp" />
          </div>
          <div className="visual-caption"><span><i /> Plataforma pronta para integrar</span><span>WEB · DB · DNS · SMTP</span></div>
        </div>
        <div className="visual-bottom"><span>DEVOPS MONITORING PLATFORM</span><span>BUILT FOR CLARITY <ArrowUpRight size={13} /></span></div>
      </section>

      <section className="login-panel">
        <div className="mobile-brand"><BrandMark /></div>
        <div className="login-card-wrap">
          <div className="login-heading">
            <div className="login-icon"><LockKeyhole size={19} /></div>
            <span className="eyebrow">ÁREA RESTRITA</span>
            <h2>Bem-vindo de volta</h2>
            <p>Entre com suas credenciais para acessar o painel de monitoramento.</p>
          </div>

          {params.reason === "configuration" && (
            <p className="setup-notice" role="status">
              O login está aguardando a configuração do projeto Supabase. Defina as variáveis públicas em <code>web/.env.local</code>.
            </p>
          )}

          <Suspense fallback={<div className="login-loading" aria-label="Carregando formulário" />}>
            <LoginForm configured={configured} redirectTo={safeRedirect} />
          </Suspense>

          <div className="login-security"><ShieldCheck size={16} /><span>Autenticação protegida pelo Supabase</span><i /></div>
        </div>
        <div className="login-footer"><span>© 2026 DevOps Monitor</span><span>Ambiente acadêmico · Acesso autorizado</span></div>
      </section>
    </main>
  );
}

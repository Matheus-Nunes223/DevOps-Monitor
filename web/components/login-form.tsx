"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Eye, EyeOff, LoaderCircle, LockKeyhole, Mail } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type LoginFormProps = {
  configured: boolean;
  redirectTo: string;
};

export function LoginForm({ configured, redirectTo }: LoginFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);

    if (!configured) {
      setMessage("O acesso ainda não está configurado. Consulte o administrador do projeto.");
      return;
    }

    setPending(true);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        setMessage("Não foi possível entrar com essas credenciais. Confira o e-mail e a senha.");
        return;
      }

      router.replace(redirectTo);
      router.refresh();
    } catch {
      setMessage("Não foi possível conectar ao serviço de autenticação. Tente novamente.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <div className="form-field">
        <label htmlFor="email">E-mail</label>
        <div className="input-wrap">
          <Mail size={17} aria-hidden="true" />
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="username"
            placeholder="nome@empresa.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            disabled={pending}
          />
        </div>
      </div>

      <div className="form-field">
        <div className="label-row">
          <label htmlFor="password">Senha</label>
          <span className="secure-note"><LockKeyhole size={12} /> Acesso protegido</span>
        </div>
        <div className="input-wrap">
          <LockKeyhole size={17} aria-hidden="true" />
          <Input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            placeholder="Digite sua senha"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            disabled={pending}
            minLength={6}
          />
          <button
            className="password-toggle"
            type="button"
            aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
            aria-pressed={showPassword}
            onClick={() => setShowPassword((current) => !current)}
          >
            {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
          </button>
        </div>
      </div>

      {message && <p className="form-message" role="alert">{message}</p>}

      <Button className="login-submit" type="submit" disabled={pending}>
        {pending ? <LoaderCircle size={17} className="spin" /> : null}
        <span>{pending ? "Validando acesso…" : "Entrar no painel"}</span>
        {!pending ? <ArrowRight size={17} /> : null}
      </Button>

      <p className="login-help">Acesso restrito a operadores autorizados.</p>
    </form>
  );
}

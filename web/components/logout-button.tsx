import { LogOut } from "lucide-react";
import { signOut } from "@/app/(dash)/actions";

export function LogoutButton() {
  return (
    <form action={signOut}>
      <button className="logout-button" type="submit">
        <LogOut size={16} aria-hidden="true" />
        <span>Sair da conta</span>
      </button>
    </form>
  );
}

"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Icons } from "@/components/icons";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return <div className="w-24 h-8 bg-panel-2 rounded-md animate-pulse" />;

  return (
    <div className="flex bg-panel-2 p-1 rounded-md border border-border">
      <button
        onClick={() => setTheme("light")}
        className={`p-1.5 rounded-sm transition-colors ${theme === "light" ? "bg-panel shadow text-primary" : "text-muted hover:text-text"}`}
        title="Claro"
      >
        <Icons.Sun className="w-4 h-4" />
      </button>
      <button
        onClick={() => setTheme("system")}
        className={`p-1.5 rounded-sm transition-colors ${theme === "system" ? "bg-panel shadow text-primary" : "text-muted hover:text-text"}`}
        title="Sistema"
      >
        <Icons.System className="w-4 h-4" />
      </button>
      <button
        onClick={() => setTheme("dark")}
        className={`p-1.5 rounded-sm transition-colors ${theme === "dark" ? "bg-panel shadow text-primary" : "text-muted hover:text-text"}`}
        title="Escuro"
      >
        <Icons.Moon className="w-4 h-4" />
      </button>
    </div>
  );
}

export function Header() {
  return (
    <header className="h-16 bg-panel border-b border-border flex items-center justify-between px-6 sticky top-0 z-10">
      <div className="md:hidden font-bold text-primary">TDE Redes Neurais</div>
      <div className="hidden md:flex flex-1"></div>
      <div className="flex items-center gap-4">
        <ThemeToggle />
      </div>
    </header>
  );
}

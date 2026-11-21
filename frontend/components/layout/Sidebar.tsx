"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icons } from "@/components/icons";

const menuItems = [
  { href: "/", label: "Dashboard", icon: Icons.Dashboard },
  { href: "/treinar", label: "Treinar Modelo", icon: Icons.Play },
  { href: "/comparar", label: "Comparar Runs", icon: Icons.Compare },
  { href: "/simulador", label: "Simulador", icon: Icons.Chart },
  { href: "/dados", label: "Dataset", icon: Icons.History },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-panel border-r border-border min-h-screen flex flex-col hidden md:flex">
      <div className="h-16 flex items-center px-6 border-b border-border">
        <h1 className="font-bold text-lg text-primary tracking-tight">TDE Redes Neurais</h1>
      </div>
      <nav className="flex-1 p-4 space-y-2">
        {menuItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${
                isActive ? "bg-panel-2 text-primary font-medium" : "text-muted hover:text-text hover:bg-panel-2"
              }`}
            >
              <Icon className="w-5 h-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-border text-xs text-muted">
        <p>PRF DATATRAN 2024</p>
        <p>Modelo MLP from scratch</p>
      </div>
    </aside>
  );
}

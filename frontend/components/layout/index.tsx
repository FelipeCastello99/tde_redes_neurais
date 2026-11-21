import { Icons } from "@/components/icons";

export function PageHeader({ title, description }: { title: string, description?: string }) {
  return (
    <div className="mb-8">
      <h1 className="text-3xl font-bold tracking-tight text-text">{title}</h1>
      {description && <p className="text-muted mt-2 text-lg">{description}</p>}
    </div>
  );
}

export function StatCard({ 
    title, value, description, icon: Icon, trend
}: { 
    title: string, value: string | number, description?: string, icon?: React.ElementType, trend?: { value: number, isGood: boolean }
}) {
  return (
    <div className="bg-panel border border-border rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-muted">{title}</h3>
        {Icon && <Icon className="w-4 h-4 text-muted" />}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-text">{value}</span>
        {trend && (
          <span className={`text-xs font-medium ${trend.isGood ? 'text-success' : 'text-danger'}`}>
            {trend.value > 0 ? '+' : ''}{trend.value}%
          </span>
        )}
      </div>
      {description && <p className="text-xs text-muted mt-1">{description}</p>}
    </div>
  );
}

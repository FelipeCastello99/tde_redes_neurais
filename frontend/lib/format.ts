export function formatNumber(num: number, decimals = 2): string {
    return new Intl.NumberFormat('pt-BR', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(num);
  }
  
  export function formatPercent(num: number, decimals = 1): string {
    return new Intl.NumberFormat('pt-BR', {
      style: 'percent',
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(num);
  }
  
  export function formatTime(seconds: number): string {
    if (!seconds && seconds !== 0) return "--:--";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    if (m > 0) return `${m} min ${s} s`;
    return `${s} s`;
  }
  
  export function formatDate(isoString: string): string {
    if (!isoString) return "";
    const date = new Date(isoString);
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }

"use client";

import { PageHeader } from "@/components/layout";
import { Icons } from "@/components/icons";
import { formatNumber, formatPercent } from "@/lib/format";

export default function DatasetPage() {
  const targetClasses = [
    { label: "Com Vítimas Feridas", count: 56194 },
    { label: "Sem Vítimas", count: 11782 },
    { label: "Com Vítimas Fatais", count: 5225 }
  ];
  const total = 73201;

  const excluded = [
    { name: "classificacao_acidente", reason: "Define o alvo (vazamento)." },
    { name: "mortos, feridos, pessoas", reason: "São a consequência pós-acidente (vazamento)." },
    { name: "id", reason: "Apenas identificador único." },
    { name: "data_inversa", reason: "As datas criam atalhos temporais para 2024 que não generalizam." },
    { name: "latitude, longitude", reason: "Exige transformações espaciais complexas e já temos BR/KM." },
    { name: "municipio", reason: "Alta cardinalidade (1.834)." }
  ];

  return (
    <div className="max-w-[1000px] mx-auto space-y-8 pb-12">
      <PageHeader 
        title="Dicionário do Dataset" 
        description="Acidentes em Rodovias Federais agrupados por ocorrência (PRF, 2024)."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-panel border border-border p-6 rounded-xl shadow-sm space-y-4">
          <div className="flex items-center gap-3 text-primary mb-2">
            <Icons.Dashboard className="w-5 h-5" />
            <h2 className="font-bold text-lg">Volumetria</h2>
          </div>
          <ul className="space-y-3 text-sm text-text">
            <li className="flex justify-between border-b border-border pb-1">
              <span className="text-muted">Órgão</span>
              <span className="font-medium">Polícia Rodoviária Federal (DIOP)</span>
            </li>
            <li className="flex justify-between border-b border-border pb-1">
              <span className="text-muted">Total de Registros</span>
              <span className="font-medium">73.201</span>
            </li>
            <li className="flex justify-between border-b border-border pb-1">
              <span className="text-muted">Variáveis Brutas</span>
              <span className="font-medium">30 colunas</span>
            </li>
            <li className="flex justify-between pb-1">
              <span className="text-muted">Valores Nulos</span>
              <span className="font-medium">0% (nas colunas vitais)</span>
            </li>
          </ul>
        </div>

        <div className="bg-panel border border-border p-6 rounded-xl shadow-sm space-y-4">
          <div className="flex items-center gap-3 text-primary mb-2">
            <Icons.Chart className="w-5 h-5" />
            <h2 className="font-bold text-lg">Distribuição da Gravidade</h2>
          </div>
          <div className="space-y-3 mt-4">
            {targetClasses.map(c => (
              <div key={c.label} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-text">{c.label}</span>
                  <span className="font-mono text-muted">{formatNumber(c.count, 0)} ({formatPercent(c.count / total)})</span>
                </div>
                <div className="h-2 w-full bg-panel-2 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full ${c.label.includes('Fatais') ? 'bg-danger' : c.label.includes('Feridas') ? 'bg-warning' : 'bg-success'}`}
                    style={{ width: `${(c.count / total) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-panel border border-border p-6 rounded-xl shadow-sm space-y-6">
        <div className="flex items-center gap-3 text-primary">
          <Icons.Warning className="w-5 h-5" />
          <h2 className="font-bold text-lg">Prevenção de Vazamento de Dados (Data Leakage)</h2>
        </div>
        <p className="text-sm text-text max-w-3xl">
          Para garantir que a rede neural não &quot;decore&quot; a resposta, diversas variáveis que são consequência direta do acidente 
          foram removidas. O modelo deve prever a letalidade analisando apenas o cenário (horário, clima, traçado, tipo de acidente).
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {excluded.map((item, idx) => (
            <div key={idx} className="bg-danger/5 border border-danger/10 p-3 rounded-lg flex items-start gap-3">
              <Icons.Trash className="w-4 h-4 text-danger shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-bold text-text font-mono">{item.name}</p>
                <p className="text-xs text-muted mt-1">{item.reason}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-warning/10 border border-warning/20 p-6 rounded-xl shadow-sm text-warning flex gap-3">
        <Icons.Warning className="w-6 h-6 shrink-0" />
        <div className="space-y-2">
          <h3 className="font-bold">Limitações do Estudo</h3>
          <p className="text-sm">
            Este é um protótipo acadêmico. A base de dados aberta não informa a velocidade dos veículos no impacto,
            o uso de cinto de segurança, tempo de resposta do socorro ou integridade estrutural da via. Sem essas medições cruciais,
            o teto de previsibilidade estatística do modelo de redes neurais fica estagnado e é normal observar o ROC-AUC travado
            na casa dos ~0.70 a 0.80.
          </p>
        </div>
      </div>
    </div>
  );
}

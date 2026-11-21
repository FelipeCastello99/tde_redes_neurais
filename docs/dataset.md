# Dataset — DATATRAN 2024 (PRF)

> Documento de referência da base usada no TDE. Toda alteração de fonte,
> versão ou hash deve ser registrada aqui e refletida em `backend.md` §3.

---

## 1. Identificação e fonte

| Campo | Valor |
|---|---|
| Nome | Acidentes em Rodovias Federais — DATATRAN (agrupados por ocorrência) |
| Órgão responsável | Polícia Rodoviária Federal (PRF) — Diretoria de Operações (DIOP) |
| Página oficial | https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf |
| Dicionário oficial | https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dicionario-acidentes |
| Ano de referência | 2024 |
| Arquivo | `datatran2024.csv` |
| Tema | Transporte / segurança viária / políticas públicas |
| Objetivo original | Divulgar, para transparência e pesquisa, os boletins de acidente (BAT) consolidados pela PRF |
| Granularidade | **1 linha = 1 ocorrência de acidente** (visão "agrupada por ocorrência") |
| Dados pessoais | Não. Registros agregados por ocorrência, sem identificação de vítimas |

> A página da PRF passou a hospedar os arquivos no Google Drive. O link direto
> usado pelo script é
> `https://drive.google.com/uc?export=download&id=14lB0vqMFkaZj8HZ44b0njYgxs9nAN8KO`.
> Se ele mudar, baixe manualmente pela página oficial e coloque o CSV em
> `data/raw/datatran2024.csv`.

## 2. Integridade e reprodutibilidade

| Item | Valor |
|---|---|
| Tamanho do CSV | 21.365.616 bytes |
| SHA-256 do CSV | `7d26e6f4528c2ca2636a8fea2c5bc8755a0ff6a182d82c238a8793b016e4366d` |
| SHA-256 do ZIP oficial | `905dac836867297b261e4edefff6cdb470809814e7e1796b3f2f57517099d165` |
| Registros | 73.202 (73.203 linhas com cabeçalho) |
| Colunas | 30 |
| Download | `make fetch` (ou `python scripts/fetch_data.py`) |
| Verificação | `make data-check` (ou `python scripts/fetch_data.py --check`) |

O script valida hash, tamanho, cabeçalho exato, contagem de linhas e
balanceamento do alvo. Se a PRF publicar uma revisão do arquivo, rode com
`--allow-hash-mismatch` **apenas depois** de conferir a diferença e atualizar
este documento.

## 3. Formato e leitura

| Propriedade | Valor |
|---|---|
| Codificação | **latin-1** (ISO-8859-1); não abre como UTF-8 |
| Separador | ponto e vírgula (`;`) |
| Delimitador de texto | aspas duplas (`"`) |
| Decimal | **vírgula** (afeta `km`, `latitude`, `longitude`) |
| Data | `AAAA-MM-DD` |
| Hora | `HH:MM:SS` |

Leitura recomendada:

```python
import pandas as pd

df = pd.read_csv(
    "data/raw/datatran2024.csv",
    sep=";",
    encoding="latin-1",
    decimal=",",          # km, latitude e longitude
    dtype={"br": "Int64", "km": "float64"},
)
```

## 4. Volumetria e qualidade

- 73.202 ocorrências, **`id` único** (0 duplicatas de id e 0 linhas repetidas).
- 27 UFs, 1.834 municípios, 69 causas, 17 tipos de acidente, 659 valores de
  `tracado_via` (combinações de geometria).
- `km` varia de 0 a 1.470,0 (230 registros acima de 1.000 km, compatíveis com
  a extensão de rodovias como a BR-163); **sem valores ausentes**.
- `latitude`/`longitude` preenchidas em 100% das linhas, mas em formato textual
  com vírgula — exigem conversão antes de uso numérico.
- Apenas **1 registro** com `classificacao_acidente = "NA"` (alvo indefinido).
- Consistência interna: os 11.782 registros com `mortos = 0` e `feridos = 0`
  coincidem com a classe "Sem Vítimas".
- Totais: **6.163 mortos** e **84.595 feridos** no ano.
- Acentos e cedilhas aparecem corretamente apenas em latin-1.

Distribuição do alvo:

| `classificacao_acidente` | Registros | % |
|---|---:|---:|
| Com Vítimas Feridas | 56.194 | 76,8% |
| Sem Vítimas | 11.782 | 16,1% |
| Com Vítimas Fatais | 5.225 | 7,1% |
| `NA` | 1 | ~0,0% |

## 5. Dicionário das variáveis

| # | Coluna | Tipo | Significado | Observações |
|---:|---|---|---|---|
| 1 | `id` | inteiro | Identificador único da ocorrência | Chave; excluído do modelo |
| 2 | `data_inversa` | data | Data do acidente | Excluída (não generaliza; ano único) |
| 3 | `dia_semana` | categórica | Dia da semana | 7 valores |
| 4 | `horario` | hora | Horário do acidente | Base para `hora_sin`/`hora_cos` |
| 5 | `uf` | categórica | Unidade da Federação | 27 valores |
| 6 | `br` | inteiro | Número da rodovia federal | 0–499 |
| 7 | `km` | decimal | Quilômetro do trecho | Decimal com vírgula |
| 8 | `municipio` | categórica | Município da ocorrência | 1.834 valores; alta cardinalidade |
| 9 | `causa_acidente` | categórica | Causa provável atribuída | 69 valores |
| 10 | `tipo_acidente` | categórica | Tipo de colisão/evento | 17 valores |
| 11 | `classificacao_acidente` | categórica | Gravidade registrada | **Alvo** |
| 12 | `fase_dia` | categórica | Iluminação natural | Pleno dia, Plena noite, Amanhecer, Anoitecer |
| 13 | `sentido_via` | categórica | Sentido do tráfego | Crescente, Decrescente, Não informado |
| 14 | `condicao_metereologica` | categórica | Clima no momento | 10 valores |
| 15 | `tipo_pista` | categórica | Configuração da pista | Simples, Dupla, Múltipla |
| 16 | `tracado_via` | categórica | Geometria do trecho | 659 combinações; será reduzido ao 1º termo |
| 17 | `uso_solo` | booleana | Trecho em área urbana? | Sim/Não |
| 18 | `pessoas` | inteiro | Total de pessoas envolvidas | Pós-evento; excluída |
| 19 | `mortos` | inteiro | Total de mortos | **Origem do alvo binário**; excluída das features |
| 20 | `feridos_leves` | inteiro | Feridos leves | Pós-evento; excluída |
| 21 | `feridos_graves` | inteiro | Feridos graves | Pós-evento; excluída |
| 22 | `ilesos` | inteiro | Pessoas ilesas | Pós-evento; excluída |
| 23 | `ignorados` | inteiro | Estado ignorado | Pós-evento; excluída |
| 24 | `feridos` | inteiro | Total de feridos | Pós-evento; excluída |
| 25 | `veiculos` | inteiro | Total de veículos envolvidos | 1–?; usada como feature |
| 26 | `latitude` | decimal | Latitude da ocorrência | Decimal com vírgula |
| 27 | `longitude` | decimal | Longitude da ocorrência | Decimal com vírgula |
| 28 | `regional` | categórica | Superintendência regional (SPRF) | Cardinalidade média; opcional |
| 29 | `delegacia` | categórica | Delegacia da PRF | Cardinalidade alta; opcional |
| 30 | `uop` | categórica | Unidade Operacional | Cardinalidade alta; opcional |

## 6. Variável-alvo

### 6.1 `fatal_binario` (padrão)

```python
y = (df["mortos"] > 0).astype("int8")
```

- Classe 0 (`sem_vitima_fatal`): 67.977 (92,9%)
- Classe 1 (`vitima_fatal`): 5.225 (7,1%)

### 6.2 `gravidade_3_classes`

| Índice | Classe | Registros |
|---:|---|---:|
| 0 | Sem Vítimas | 11.782 |
| 1 | Com Vítimas Feridas | 56.194 |
| 2 | Com Vítimas Fatais | 5.225 |

O registro com `"NA"` é descartado (1 linha).

## 7. Colunas excluídas e motivo

| Coluna(s) | Motivo |
|---|---|
| `classificacao_acidente`, `mortos`, `feridos`, `feridos_leves`, `feridos_graves`, `ilesos`, `ignorados`, `pessoas` | **Vazamento**: são consequência do acidente e/ou definem o alvo |
| `id` | Identificador sem poder preditivo |
| `data_inversa` | Ano único (2024); data exata não generaliza e criaria atalho |
| `latitude`, `longitude` | Texto com vírgula e geolocalização precisa; opcional, fora do padrão |
| `municipio` | 1.834 categorias (alta cardinalidade) — opcional |
| `regional`, `delegacia`, `uop` | Alta cardinalidade administrativa — opcional, desligadas por padrão |

## 8. Derivações previstas

| Nova feature | Origem | Regra |
|---|---|---|
| `hora_sin`, `hora_cos` | `horario` | Codificação cíclica de 24 h |
| `is_fim_semana` | `dia_semana` | sábado ou domingo |
| `tracado_principal` | `tracado_via` | Texto antes do primeiro `;` (ex.: `"Curva;Declive"` → `"Curva"`) |
| `log_veiculos` | `veiculos` | `log1p`, opcional por configuração |
| `km` | `km` | Conversão de vírgula decimal para `float` |

## 9. Limitações conhecidas

1. **Subnotificação e qualidade do registro** variam por unidade da PRF.
2. `causa_acidente` é a causa *provável* atribuída no boletim, não uma medição.
3. A base não contém velocidade no impacto, uso de cinto, tipo de veículo,
   condições do condutor nem tempo de resposta do socorro — fatores relevantes
   para a gravidade. Isso limita o teto de desempenho do modelo (ROC-AUC
   esperado entre 0,70 e 0,80) e deve constar na análise crítica.
4. 2024 é um recorte de um ano; conclusões não se generalizam automaticamente
   para outros períodos.
5. A visão "agrupada por ocorrência" perde detalhes por pessoa envolvida; a
   visão "por pessoa" existe na mesma página, mas não é usada neste TDE.

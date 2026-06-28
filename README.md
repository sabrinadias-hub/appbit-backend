# App BiT — Matching Inclusivo B2B

**Plataforma web responsiva que conecta empresas com metas ESG a profissionais de grupos sub-representados.**

> Hackathon · Junho 2026 · Sabrina Dias de Oliveira · sabrina@svmarketing.online

🌐 **App ao vivo:** https://app-bit-connect.lovable.app  
⚙️ **API:** https://appbit-backend.onrender.com  
📖 **Documentação interativa:** https://appbit-backend.onrender.com/docs

---

## Visão geral

O App BiT combina um agente de scoring inteligente com dados reais de geolocalização (Vísent CDRView / Anatel) para identificar onde talentos qualificados estão — e onde o recrutamento digital tradicional falha por conta da **exclusão digital**.

> **Problema central:** candidatos de grupos sub-representados em regiões com baixa cobertura de rede (3G precário ou sem sinal) são invisíveis para plataformas de recrutamento convencionais. O App BiT usa dados de conectividade não para encontrá-los digitalmente, mas para alertar empresas sobre onde estratégias além do digital são necessárias.

---

## Stack tecnológica

| Camada | Tecnologias |
|---|---|
| **Frontend** | React + TypeScript + Tailwind CSS · TanStack Router · MapLibre GL · Lovable.dev |
| **Backend** | Python 3.11 · FastAPI · Uvicorn · Pandas · Pydantic v2 |
| **Infraestrutura** | Render.com (deploy automático via GitHub) · Neon PostgreSQL (provisionado) |
| **Dataset** | Vísent CDRView (Anatel) — 132 antenas reais · 200K perfis emulados |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│              FRONTEND (Lovable / React)              │
│                                                      │
│  Dashboard B2B   Publicar Vaga   Shortlist           │
│  Minhas Vagas    Relatório ESG   Saúde do Time       │
│  Dashboard B2C   Cadastro        Survey              │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS / REST
┌──────────────────────▼──────────────────────────────┐
│              BACKEND (FastAPI / Render)              │
│                                                      │
│  POST /match           POST /match/candidato         │
│  GET  /vagas           GET  /insights                │
│  POST /survey          GET  /survey/relatorio        │
└──────────┬──────────────────────┬───────────────────┘
           │                      │
  ┌────────▼────────┐   ┌─────────▼────────┐
  │  candidatos.json│   │  CDRView CSVs     │
  │  vagas.json     │   │  antenas_flp.csv  │
  │  (mock data)    │   │  assinantes.csv   │
  └─────────────────┘   └──────────────────┘
```

---

## Como executar localmente

**Pré-requisitos:** Python 3.11+, Git

```bash
git clone https://github.com/sabrinadias-hub/appbit-backend
cd appbit-backend
pip install -r requirements.txt
uvicorn main:app --reload
```

API disponível em `http://localhost:8000`  
Documentação interativa em `http://localhost:8000/docs`

---

## Endpoints da API

### `POST /match` — empresa → candidatos

Recebe requisitos de vaga e retorna shortlist ordenada por score de compatibilidade.

**Request:**
```json
{
  "empresa_id": 1,
  "vaga": {
    "titulo": "Desenvolvedora Frontend",
    "skills": ["React", "TypeScript"],
    "nivel": "Pleno",
    "regiao": "florianópolis"
  },
  "filtros": {
    "anti_vies": true,
    "diversidade_minima": 0,
    "pesos": { "raca": 40, "genero": 30, "pcd": 30 }
  }
}
```

**Response:**
```json
{
  "candidatos": [
    {
      "candidato_id": 101,
      "nome": null,
      "score_match": 85,
      "badge_diversidade": true,
      "skills": ["React", "TypeScript", "CSS"],
      "soft_skills": ["Comunicação", "Trabalho em equipe"],
      "funcao_desejada": "Desenvolvedora Frontend",
      "motivo": "2 de 2 skills compatíveis. Nível alinhado.",
      "contribuicao_diversidade": {
        "score_ponderado": 70,
        "dimensoes_atendidas": ["raca", "genero"]
      }
    }
  ],
  "total_analisados": 15,
  "diversidade_resultado": 73
}
```

> Quando `anti_vies: true`, os campos `nome`, `idade` e `foto` são retornados como `null`. O recrutador vê apenas competências.

---

### `POST /match/candidato` — candidato → vagas

Recebe perfil do candidato e retorna vagas compatíveis com score real.

**Request:**
```json
{
  "skills": ["React", "TypeScript"],
  "nivel": "pleno",
  "regiao": "florianópolis",
  "dimensoes_diversidade": ["genero", "raca"]
}
```

**Response:**
```json
{
  "vagas_recomendadas": [
    {
      "vaga_id": 1,
      "titulo": "Desenvolvedora Frontend",
      "empresa": "Lumen S.A.",
      "score_compatibilidade": 85,
      "skills_em_comum": ["react", "typescript"],
      "motivo": "2 de 4 skills compatíveis. Nível alinhado.",
      "alinhamento_esg": ["genero"],
      "metas_esg_empresa": ["genero", "raca", "pcd"]
    }
  ],
  "total_analisadas": 8,
  "total_com_match": 3
}
```

---

### `GET /vagas` — lista de vagas com métricas

Retorna todas as vagas com contagem de candidatos aptos e percentual de diversidade no pool.

**Response:**
```json
{
  "vagas": [
    {
      "vaga_id": 1,
      "titulo": "Desenvolvedora Frontend",
      "total_candidatos_aptos": 8,
      "percentual_diversidade": 75,
      "metas_esg": ["genero", "raca", "pcd"]
    }
  ],
  "total": 8
}
```

---

### `GET /insights` — dados CDRView

Retorna dados reais de concentração de talentos por região com cobertura de rede.

**Response:**
```json
{
  "mapa_talentos": [
    {
      "regiao": "Cbd Beiramar",
      "municipio": "Florianópolis",
      "concentracao": 87,
      "cobertura_rede": "5G",
      "perfis_disponiveis": 12400,
      "lat_centro": -27.5908,
      "lng_centro": -48.5490
    }
  ]
}
```

---

### `POST /survey` — survey de bem-estar

Recebe respostas anônimas em escala Likert 1–5.

**Request:**
```json
{
  "momento": "mensal",
  "p1": 4,
  "p2": 5,
  "p3": 3,
  "p4": 4,
  "p5": 4
}
```

Valores de `momento`: `"mensal"` ou `"processo_seletivo"`

---

### `GET /survey/relatorio` — relatório agregado

```
GET /survey/relatorio?momento=mensal
```

**Response:**
```json
{
  "momento": "mensal",
  "total_respostas": 12,
  "medias": [
    { "pergunta": "Como está seu nível de estresse no trabalho?", "media": 3.8, "max": 5 }
  ],
  "nota_anonimato": "Respostas anônimas — nenhum dado individual é compartilhado com a empresa."
}
```

---

## Lógica de scoring

### Score de compatibilidade (0–100)

| Critério | Peso | Cálculo |
|---|---|---|
| Skills em comum | 60% | (skills em comum / skills da vaga) × 60 |
| Nível | 25% | +25 se nível do candidato = nível da vaga |
| Região | 15% | +15 se região do candidato = região da vaga |

### Dimensões de diversidade suportadas

| Dimensão | Chave |
|---|---|
| Raça/etnia | `raca` |
| Gênero | `genero` |
| Pessoa com deficiência | `pcd` |
| LGBTQIA+ | `lgbtqia` |
| 50 anos ou mais | `50mais` |
| Pessoa indígena | `indigena` |

---

## Funcionalidades implementadas

### Obrigatórias do MVP ✅

| Funcionalidade | Rota |
|---|---|
| Publicação de vaga com skills, nível e região | `/publicar-vaga` |
| Endpoint /match com shortlist + score + badge | `POST /match` |
| Interface responsiva com tela de shortlist | `/shortlist` |
| Métricas básicas de diversidade | Dashboard B2B |
| README com instruções e exemplos | Este arquivo |

### Opcionais implementadas ✅

| Funcionalidade | Rota |
|---|---|
| Mapa interativo via Vísent CDRView | Dashboard B2B |
| Filtro anti-viés com explicabilidade | `/shortlist` — campo `motivo` |
| Relatório de diversidade exportável em PDF | `/relatorio-esg` |
| Dashboard de saúde do time | `/saude-time` |
| Integração B2C para matching em tempo real | `POST /match/candidato` |

---

## Dataset Vísent CDRView

- **`antenas_flp.csv`** — 132 antenas Anatel reais em Florianópolis com coordenadas geográficas, cluster de cobertura e tecnologia (5G/4G/3G)
- **`assinantes.csv`** — 200.000 perfis emulados de assinantes com cluster residencial (`home_cluster`)

> **Nota metodológica sobre exclusão digital:** o mapa usa dados de cobertura de rede não apenas para localizar candidatos, mas para identificar regiões onde o recrutamento digital tradicional falha. Regiões com cobertura 3G precária ou ausente indicam onde candidatos qualificados de grupos sub-representados podem estar invisíveis para plataformas convencionais — sinalizando a necessidade de estratégias de atração além do digital.

---

## Estrutura do repositório

```
appbit-backend/
├── main.py              # FastAPI app — todos os endpoints
├── candidatos.json      # 15 candidatos mock com skills e dimensões
├── vagas.json           # 8 vagas com metas ESG
├── antenas_flp.csv      # Dataset CDRView — antenas Anatel
├── assinantes.csv       # Dataset CDRView — perfis emulados
├── requirements.txt     # Dependências Python
├── runtime.txt          # Python 3.11.0 (Render)
└── README.md            # Esta documentação
```

---

## Decisões técnicas

| Decisão | Motivo |
|---|---|
| MapLibre GL em vez de Leaflet | Leaflet causava crash no ambiente Lovable; MapLibre usa WebGL puro, sem manipulação de DOM, sem chave de API |
| Armazenamento em memória para survey | psycopg2 incompatível com Python 3.14 no Render; solução adequada para demo com anonimato garantido |
| `window.print()` para PDF | html2canvas falhou no ambiente Lovable; print nativo com `@media print` gera PDF limpo sem dependências |
| Score anti-viés declarativo | Conforme orientação técnica do hackathon: "badge de diversidade pode ser campo declarativo simples para o MVP" |
| Dois endpoints de match | Matching bidirecional: empresa → candidatos E candidato → vagas — integração completa B2B + B2C |

---

## Dependências

```
fastapi==0.138.1
uvicorn==0.49.0
pandas==3.0.3
pydantic==2.13.4
```

---

*Construído com FastAPI · Lovable · MapLibre GL · Vísent CDRView*

# App BiT — Matching Inclusivo B2B

Plataforma de matching entre empresas com metas ESG e talentos de grupos sub-representados.

## Sobre o projeto

O App BiT conecta empresas que buscam diversidade real com candidatos qualificados de grupos historicamente excluídos do mercado de trabalho. O sistema usa um algoritmo de matching baseado em skills e um filtro anti-viés que oculta dados sensíveis (nome, idade, foto) durante a triagem — garantindo que a decisão seja feita por competência, não por aparência.

## Dataset CDRView / Vísent-Anatel

O mapa de talentos do dashboard usa dados reais do dataset CDRView (Vísent / Anatel) para Florianópolis:

- **antenas_flp.csv** — 132 antenas ERB da Anatel com coordenadas reais (lat/lon), cluster e município
- **assinantes.csv** — 200 mil perfis sintéticos de assinantes com cluster de mobilidade, faixa etária e padrão de renda

**Uso no desafio:** o mapa mostra a concentração de talentos por região geográfica de Florianópolis, com indicação da qualidade de conectividade (5G / 4G / 3G) por zona. Isso permite à empresa entender onde estão os candidatos de grupos sub-representados antes de publicar uma vaga.

**Nota metodológica:** os dados de concentração e cobertura de rede são reais (Anatel). Os percentuais de diversidade por zona são estimativas regionais baseadas no perfil socioeconômico de cada cluster — declarados explicitamente no dashboard.

## Funcionalidades

- **Mapa de calor interativo** — concentração de grupos sub-representados por zona de Florianópolis, com filtros por dimensão (Raça/etnia, Gênero, PCD, LGBTQIA+)
- **Matching por skills** — score calculado pela proporção de skills compatíveis com a vaga
- **Filtro anti-viés** — quando ativado, oculta nome, idade e foto dos candidatos na triagem
- **Score ESG ponderado** — cada candidato recebe um score de diversidade baseado nas dimensões configuradas pela empresa
- **Dashboard B2B** — métricas de pipeline inclusivo, mapa CDRView e vagas publicadas
- **Área do candidato** — cadastro de perfil com skills e dimensões de diversidade (dados salvos localmente)

## Endpoints da API

Base URL: `https://appbit-backend.onrender.com`

### GET /
Verifica se a API está online.

**Resposta:**
```json
{
  "status": "App BiT API online",
  "docs": "/docs"
}
```

### GET /insights
Retorna dados reais do CDRView — concentração de perfis por cluster de mobilidade com coordenadas das antenas Anatel.

**Resposta:**
```json
{
  "mapa_talentos": [
    {
      "regiao": "Cbd Beiramar",
      "municipio": "Florianopolis",
      "concentracao": 44,
      "cobertura_rede": "5G",
      "perfis_disponiveis": 17919,
      "lat_centro": -27.589,
      "lng_centro": -48.548
    }
  ]
}
```

### POST /match
Realiza o matching de candidatos para uma vaga, com filtro anti-viés e score de diversidade ponderado.

**Corpo da requisição:**
```json
{
  "empresa_id": 1,
  "vaga": {
    "titulo": "Desenvolvedor React",
    "skills": ["React", "TypeScript"],
    "nivel": "Pleno",
    "regiao": "São Paulo"
  },
  "filtros": {
    "anti_vies": true,
    "diversidade_minima": 0,
    "pesos": {
      "raca": 30,
      "genero": 25,
      "pcd": 20,
      "lgbtqia": 15,
      "50mais": 5,
      "indigena": 5
    }
  }
}
```

**Resposta:**
```json
{
  "candidatos": [
    {
      "candidato_id": 101,
      "nome": "Candidato(a) #101",
      "idade": null,
      "foto": null,
      "score_match": 100,
      "badge_diversidade": true,
      "skills": ["React", "TypeScript", "CSS"],
      "lat": -23.55,
      "lng": -46.63,
      "motivo": "2 de 2 skills compatíveis. Nível alinhado.",
      "contribuicao_diversidade": {
        "score_ponderado": 100,
        "dimensoes_atendidas": ["raca", "genero"]
      }
    }
  ],
  "total_analisados": 10,
  "diversidade_resultado": 80
}
```

**Comportamento do anti-viés:** quando `anti_vies: true`, os campos `nome`, `idade` e `foto` retornam `null`, impedindo que vieses inconscientes influenciem a triagem.

## Dimensões de diversidade suportadas

| Dimensão | Descrição |
|---|---|
| `raca` | Raça / etnia |
| `genero` | Gênero (mulheres cis e trans) |
| `pcd` | Pessoa com deficiência |
| `lgbtqia` | LGBTQIA+ |
| `50mais` | Profissionais acima de 50 anos |
| `indigena` | Povos indígenas |

## Como rodar localmente

```bash
# Clone o repositório
git clone https://github.com/sabrinadias-hub/appbit-backend.git
cd appbit-backend

# Crie o ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt

# Inicie o servidor
uvicorn main:app --reload
```

A API estará disponível em `http://localhost:8000`.  
Documentação interativa: `http://localhost:8000/docs`

## Estrutura do projeto

```
appbit-backend/
├── main.py              # API FastAPI com endpoints /match e /insights
├── candidatos.json      # Base de candidatos mock com skills e dimensões de diversidade
├── antenas_flp.csv      # Antenas Anatel — coordenadas reais (CDRView)
├── assinantes.csv       # Perfis sintéticos por cluster (CDRView)
├── insights_data.json   # Fallback caso os CSVs não carreguem
└── requirements.txt     # Dependências Python
```

## Stack

- **Backend:** Python 3 + FastAPI + Uvicorn + Pandas
- **Frontend:** React + TypeScript + Tailwind CSS + shadcn/ui + MapLibre GL (via Lovable)
- **Deploy:** Render.com (backend) + Lovable (frontend)
- **Dataset:** CDRView / Vísent-Anatel (Florianópolis)

## Repositório do frontend

Desenvolvido via Lovable: [App BiT — Talent Match](https://lovable.dev/projects/4569642c-66de-4de2-b95a-4512f35604d9)

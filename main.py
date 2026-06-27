import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(
    title="App BiT — API de Matching Inclusivo",
    description="Plataforma B2B de matching inclusivo com metas ESG",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
with open(BASE_DIR / "candidatos.json", encoding="utf-8") as f:
    CANDIDATOS = json.load(f)

# Carrega dados reais do CDRView (Vísent / Anatel)
def carregar_insights_cdrview():
    try:
        import pandas as pd
        antenas = pd.read_csv(BASE_DIR / "antenas_flp.csv", dtype={"ecgi": str})
        assinantes = pd.read_csv(BASE_DIR / "assinantes.csv")

        contagem = assinantes["home_cluster"].value_counts().reset_index()
        contagem.columns = ["cluster", "total"]
        total_geral = contagem["total"].sum()

        coord_cluster = antenas.groupby("cluster")[["lat", "lon"]].mean().reset_index()

        merged = contagem.merge(coord_cluster, on="cluster", how="left")
        merged = merged.merge(
            antenas[["cluster", "municipio"]].drop_duplicates("cluster"),
            on="cluster", how="left"
        )

        cobertura_map = {
            "CBD_BEIRAMAR": "5G", "CENTRO_HISTORICO": "5G", "TRINDADE": "5G",
            "UFSC": "4G", "SAO_JOSE_CENTRO": "4G", "SAO_JOSE_KOBRASOL": "4G",
            "COQUEIROS": "4G", "ESTREITO_CAPOEIRAS": "4G", "CAMPECHE": "4G",
            "LAGOA_CONCEICAO": "4G", "RESIDENCIAL_NORTE": "4G",
            "SAO_JOSE_BARREIROS": "4G", "PALHOCA_CENTRO": "3G",
            "BIGUACU_BR101_NORTE": "3G", "NORTE_ILHA": "4G",
            "CANASVIEIRAS": "4G", "INGLESES": "3G", "JURERE": "4G",
            "AEROPORTO_HLZ": "4G", "SC401_CORREDOR": "3G",
            "VIA_EXPRESSA_CORREDOR": "4G", "PALHOCA_PEDRA_BRANCA": "3G",
        }

        resultado = []
        for _, row in merged.iterrows():
            concentracao = int((row["total"] / total_geral) * 100 * 5)
            concentracao = min(concentracao, 99)
            resultado.append({
                "regiao": row["cluster"].replace("_", " ").title(),
                "municipio": row.get("municipio", "Florianópolis"),
                "concentracao": concentracao,
                "cobertura_rede": cobertura_map.get(row["cluster"], "4G"),
                "perfis_disponiveis": int(row["total"]),
                "lat_centro": round(row["lat"], 6) if pd.notna(row["lat"]) else None,
                "lng_centro": round(row["lon"], 6) if pd.notna(row["lon"]) else None,
            })

        resultado.sort(key=lambda x: x["perfis_disponiveis"], reverse=True)

        # Limpa valores NaN que o JSON não aceita
        for r in resultado:
            for k, v in r.items():
                if isinstance(v, float) and (v != v):  # NaN check
                    r[k] = None

        return resultado

    except Exception:
        with open(BASE_DIR / "insights_data.json", encoding="utf-8") as f:
            return json.load(f)

INSIGHTS = carregar_insights_cdrview()


# --- Modelos de entrada ---

class Vaga(BaseModel):
    titulo: str
    skills: List[str]
    nivel: str
    regiao: str

class FiltrosDiversidade(BaseModel):
    anti_vies: bool = True
    diversidade_minima: int = 0
    pesos: Optional[dict] = None  # ex: {"raca": 40, "genero": 30, "pcd": 30}

class MatchRequest(BaseModel):
    empresa_id: int
    vaga: Vaga
    filtros: FiltrosDiversidade


# --- Lógica de scoring ---

def calcular_score_match(candidato: dict, vaga: Vaga) -> int:
    skills_vaga = set(s.lower() for s in vaga.skills)
    skills_candidato = set(s.lower() for s in candidato["skills"])
    skills_em_comum = skills_vaga & skills_candidato

    score = 0
    if skills_vaga:
        score += int((len(skills_em_comum) / len(skills_vaga)) * 60)
    if candidato["nivel"].lower() == vaga.nivel.lower():
        score += 25
    if candidato["regiao"].lower() == vaga.regiao.lower():
        score += 15

    return min(score, 100)


def calcular_score_diversidade(candidato: dict, pesos: Optional[dict]) -> int:
    dimensoes = candidato.get("dimensoes_diversidade", [])
    if not dimensoes:
        return 0
    if not pesos:
        return min(len(dimensoes) * 25, 100)

    total_peso = sum(pesos.values())
    if total_peso == 0:
        return 0

    pontos = sum(pesos.get(d, 0) for d in dimensoes)
    return min(int((pontos / total_peso) * 100), 100)


def gerar_motivo(candidato: dict, vaga: Vaga) -> str:
    skills_vaga = set(s.lower() for s in vaga.skills)
    skills_candidato = set(s.lower() for s in candidato["skills"])
    em_comum = skills_vaga & skills_candidato
    faltando = skills_vaga - skills_candidato

    partes = []
    partes.append(f"{len(em_comum)} de {len(skills_vaga)} skills compatíveis.")
    if candidato["nivel"].lower() == vaga.nivel.lower():
        partes.append("Nível alinhado.")
    else:
        partes.append(f"Nível divergente (candidato: {candidato['nivel']}, vaga: {vaga.nivel}).")
    if faltando:
        partes.append(f"Skills ausentes: {', '.join(faltando)}.")

    return " ".join(partes)


# --- Endpoints ---

@app.post("/match")
def match_candidatos(req: MatchRequest):
    resultados = []

    for c in CANDIDATOS:
        score = calcular_score_match(c, req.vaga)
        if score == 0:
            continue

        score_div = calcular_score_diversidade(c, req.filtros.pesos)
        atende_diversidade = score_div > 0 or not req.filtros.diversidade_minima

        if req.filtros.diversidade_minima and score_div < req.filtros.diversidade_minima:
            continue

        resultados.append({
            "candidato_id": c["candidato_id"],
            "nome": "Candidato(a) #" + str(c["candidato_id"]) if req.filtros.anti_vies else c["nome"],
            "idade": None if req.filtros.anti_vies else c["idade"],
            "foto": None if req.filtros.anti_vies else c["foto"],
            "score_match": score,
            "badge_diversidade": c["badge_diversidade"],
            "skills": c["skills"],
            "lat": c["lat"],
            "lng": c["lng"],
            "motivo": gerar_motivo(c, req.vaga),
            "contribuicao_diversidade": {
                "score_ponderado": score_div,
                "dimensoes_atendidas": c["dimensoes_diversidade"]
            }
        })

    resultados.sort(key=lambda x: (x["score_match"], x["contribuicao_diversidade"]["score_ponderado"]), reverse=True)

    diversidade_resultado = sum(1 for r in resultados if r["badge_diversidade"])
    pct_diversidade = int((diversidade_resultado / len(resultados)) * 100) if resultados else 0

    return {
        "candidatos": resultados,
        "total_analisados": len(CANDIDATOS),
        "diversidade_resultado": pct_diversidade
    }


@app.get("/insights")
def get_insights():
    return {"mapa_talentos": INSIGHTS}


@app.get("/")
def root():
    return {"status": "App BiT API online", "docs": "/docs"}

import json
import os
import urllib.request
import urllib.parse
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

NEON_HOST = "ep-flat-darkness-attoqapn.c-9.us-east-1.aws.neon.tech"
NEON_USER = "neondb_owner"
NEON_PASSWORD = "npg_PCWu4Qmrjq7x"
NEON_DB = "neondb"

# Armazenamento em memória como fallback (funciona para demo)
_survey_store = []

def neon_query(sql: str, params: list = []):
    """Executa SQL no Neon via HTTP API"""
    try:
        import ssl
        url = f"https://{NEON_HOST}/sql"
        payload = json.dumps({"query": sql, "params": params}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {urllib.parse.quote(NEON_USER)}:{urllib.parse.quote(NEON_PASSWORD)}",
                "Neon-Connection-String": f"postgresql://{NEON_USER}:{NEON_PASSWORD}@{NEON_HOST}/{NEON_DB}?sslmode=require"
            }
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"Neon HTTP error: {e}")
        return None

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
with open(BASE_DIR / "vagas.json", encoding="utf-8") as f:
    VAGAS = json.load(f)

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


# --- Matching B2C (candidato → vagas) ---

class PerfilCandidato(BaseModel):
    skills: List[str]
    nivel: str
    regiao: str
    dimensoes_diversidade: Optional[List[str]] = []

@app.post("/match/candidato")
def match_vagas_para_candidato(perfil: PerfilCandidato):
    skills_candidato = set(s.lower() for s in perfil.skills)
    resultados = []

    for vaga in VAGAS:
        skills_vaga = set(s.lower() for s in vaga["skills"])
        skills_em_comum = skills_candidato & skills_vaga
        if not skills_em_comum:
            continue

        score = 0
        if skills_vaga:
            score += int((len(skills_em_comum) / len(skills_vaga)) * 60)
        if perfil.nivel.lower() == vaga["nivel"].lower():
            score += 25
        if perfil.regiao.lower() == vaga["regiao"].lower():
            score += 15
        score = min(score, 100)

        skills_faltando = list(skills_vaga - skills_candidato)
        motivo_partes = [f"{len(skills_em_comum)} de {len(skills_vaga)} skills compatíveis."]
        if perfil.nivel.lower() == vaga["nivel"].lower():
            motivo_partes.append("Nível alinhado.")
        else:
            motivo_partes.append(f"Nível divergente (seu perfil: {perfil.nivel}, vaga: {vaga['nivel']}).")
        if skills_faltando:
            motivo_partes.append(f"Skills que você pode desenvolver: {', '.join(skills_faltando)}.")

        alinhamento_esg = [d for d in perfil.dimensoes_diversidade if d in vaga.get("metas_esg", [])]

        resultados.append({
            "vaga_id": vaga["vaga_id"],
            "titulo": vaga["titulo"],
            "empresa": vaga["empresa"],
            "nivel": vaga["nivel"],
            "regiao": vaga["regiao"],
            "descricao": vaga["descricao"],
            "skills_vaga": vaga["skills"],
            "skills_em_comum": list(skills_em_comum),
            "score_compatibilidade": score,
            "motivo": " ".join(motivo_partes),
            "alinhamento_esg": alinhamento_esg,
            "metas_esg_empresa": vaga.get("metas_esg", [])
        })

    resultados.sort(key=lambda x: x["score_compatibilidade"], reverse=True)
    return {
        "vagas_recomendadas": resultados,
        "total_analisadas": len(VAGAS),
        "total_com_match": len(resultados)
    }


# --- Survey de bem-estar ---

class SurveyResposta(BaseModel):
    momento: str  # "processo_seletivo" ou "mensal"
    p1: int  # 1-5
    p2: int
    p3: int
    p4: int
    p5: int

@app.post("/survey")
def salvar_survey(resposta: SurveyResposta):
    _survey_store.append({
        "momento": resposta.momento,
        "p1": resposta.p1, "p2": resposta.p2,
        "p3": resposta.p3, "p4": resposta.p4, "p5": resposta.p5
    })
    return {"status": "ok", "mensagem": "Resposta registrada anonimamente. Obrigada!"}

@app.get("/survey/relatorio")
def relatorio_survey(momento: str = "mensal"):
    respostas = [r for r in _survey_store if r["momento"] == momento]

    perguntas_map = {
        "processo_seletivo": [
            "Como você avalia o nível de estresse neste processo?",
            "Sentiu que foi tratado(a) com respeito?",
            "As etapas foram claras e bem comunicadas?",
            "Recomendaria esta empresa para outras pessoas?",
            "Como está seu bem-estar geral no trabalho?",
        ],
        "mensal": [
            "Como está seu nível de estresse no trabalho?",
            "Sente que seu trabalho é reconhecido?",
            "Tem equilíbrio entre vida pessoal e profissional?",
            "Sente pertencimento e inclusão na equipe?",
            "Como avalia seu bem-estar geral este mês?",
        ]
    }
    perguntas = perguntas_map.get(momento, perguntas_map["mensal"])

    if not respostas:
        # Dados demo para o relatório não aparecer vazio
        respostas = [
            {"momento": momento, "p1": 4, "p2": 5, "p3": 4, "p4": 4, "p5": 4},
            {"momento": momento, "p1": 3, "p2": 4, "p3": 5, "p4": 3, "p5": 4},
            {"momento": momento, "p1": 5, "p2": 5, "p3": 4, "p4": 5, "p5": 5},
        ]

    medias = []
    for i, pergunta in enumerate(perguntas):
        key = f"p{i+1}"
        media = round(sum(r[key] for r in respostas) / len(respostas), 1)
        medias.append({"pergunta": pergunta, "media": media, "max": 5})

    return {
        "momento": momento,
        "total_respostas": len([r for r in _survey_store if r["momento"] == momento]),
        "medias": medias,
        "nota_anonimato": "Respostas anônimas — nenhum dado individual é compartilhado com a empresa."
    }

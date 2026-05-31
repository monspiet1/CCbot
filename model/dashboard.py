import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv("./.env")

st.set_page_config(
    page_title="Wing Analytics", page_icon="assets/icon.png", layout="wide"
)

st.image("assets/icon.png", width=60)  # Ajuste a largura como preferir

st.title("Wing Tutor Analytics")
st.markdown("Monitoramento em tempo real das interações e gargalos de aprendizado.")


@st.cache_data(ttl=10)
def load_data() -> pd.DataFrame:
    conn = sqlite3.connect("analytics.db")
    query = "SELECT * FROM chat_logs"
    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


df = load_data()

if df.empty:
    st.info(
        "O banco de dados ainda está vazio. Mande algumas mensagens no app Android para popular o dashboard!"
    )
    st.stop()

# 4. KPIs Principais
st.markdown("### Visão Geral")
col1, col2, col3, col4 = st.columns(4)

total_mensagens = int(len(df))

# CORREÇÃO 1 e 2: Uso do .loc para ajudar o corretor e cast explícito para int()
sessoes_unicas = len(df["thread_id"].unique())
tutoria_df = df.loc[df["is_tutoring_active"] == 1, "thread_id"]
sessoes_tutoria = len(tutoria_df.unique())

avaliacoes = df.dropna(subset=["approved"])
if not avaliacoes.empty:
    # Garantindo que o cálculo retorne um float nativo
    taxa_aprovacao = float((avaliacoes["approved"] == 1).mean() * 100)
else:
    taxa_aprovacao = 0.0

col1.metric("Total de Mensagens", total_mensagens)
# CORREÇÃO 3: metric() agora recebe inteiros explícitos
col2.metric("Sessões (Alunos)", sessoes_unicas)
col3.metric("Sessões em Tutoria", sessoes_tutoria)
col4.metric("Taxa Média de Aprovação", f"{taxa_aprovacao:.1f}%")

st.divider()

# 5. Gráficos Analíticos
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### Distribuição de Mensagens por Estágio")
    stage_counts = df["current_stage"].value_counts().reset_index()
    stage_counts.columns = pd.Index(
        ["Estágio", "Quantidade"]
    )  # Reatribuindo colunas de forma explícita

    fig_stages = px.bar(
        stage_counts,
        x="Estágio",
        y="Quantidade",
        color="Estágio",
        template="plotly_white",
    )
    st.plotly_chart(fig_stages, use_container_width=True)

with col_chart2:
    st.markdown("#### Gargalos: Aprovação vs Reprovação por Estágio")
    if not avaliacoes.empty:
        # CORREÇÃO 4: Separado o reset_index() do rename() para evitar erro de overload no nome do argumento
        aprovacoes_stage = (
            avaliacoes.groupby(["current_stage", "approved"]).size().reset_index()
        )
        aprovacoes_stage = aprovacoes_stage.rename(columns={0: "Quantidade"})

        aprovacoes_stage["Status"] = aprovacoes_stage["approved"].apply(
            lambda x: "Aprovado (Avançou)" if x == 1.0 else "Reprovado (Intervenção)"
        )

        fig_app = px.bar(
            aprovacoes_stage,
            x="current_stage",
            y="Quantidade",
            color="Status",
            barmode="group",
            color_discrete_map={
                "Aprovado (Avançou)": "#2ecc71",
                "Reprovado (Intervenção)": "#e74c3c",
            },
            template="plotly_white",
            labels={"current_stage": "Estágio Avaliado"},
        )
        st.plotly_chart(fig_app, use_container_width=True)
    else:
        st.info("Ainda não há dados de avaliação do LLM-as-a-judge.")

st.divider()

# 5.5 Análise em Lote via IA (Sob Demanda)
st.markdown("#### 🧠 Relatório Gerencial de Dúvidas (Gerado por IA)")
st.markdown(
    "Clique no botão abaixo para a IA analisar todas as interações e resumir os maiores bloqueios dos alunos."
)

# O botão impede que a API do Gemini seja chamada toda vez que a página der refresh
if st.button("Gerar Relatório de Dificuldades"):
    # Pega as mensagens dos usuários (apenas as que não estão vazias)
    # Pegamos as últimas 100 mensagens para economizar tokens e focar no que é recente
    mensagens_alunos = df["user_message"].dropna().tail(100).tolist()

    if len(mensagens_alunos) < 3:
        st.warning(
            "O banco precisa de pelo menos umas 3 mensagens de alunos para gerar uma análise útil."
        )
    else:
        # UX: Mostra um spinner girando enquanto o Gemini processa
        with st.spinner("Analisando a semântica de todas as interações..."):
            try:
                # Instancia o modelo
                llm_dash = ChatGoogleGenerativeAI(
                    model="gemini-3.1-flash-lite-preview", temperature=0.2
                )

                # Monta o Prompt como se você fosse um Coordenador Pedagógico
                prompt = f"""
                Você é um Analista de Dados Educacionais sênior.
                Abaixo está uma lista crua das últimas mensagens de alunos que estão usando nosso sistema de tutoria em Pensamento Computacional.

                MENSAGENS:
                {mensagens_alunos}

                SUA TAREFA:
                1. Agrupe as mensagens por similaridade semântica (ignore saudações irrelevantes como 'olá').
                2. Identifique os 3 a 5 principais temas técnicos ou dificuldades lógicas que mais se repetem.
                3. Escreva um relatório gerencial curto, em formato Markdown.
                4. Use Títulos (###), Bullet points e destaque os termos chave em **negrito**.
                5. Dê uma breve sugestão de como o tutor pode melhorar a abordagem para a dificuldade nº 1.
                """

                # Chama a API
                raw_content = llm_dash.invoke(prompt).content

                # TRATAMENTO: Verifica se o Gemini retornou uma lista de blocos estruturados
                if isinstance(raw_content, list):
                    # Percorre a lista e junta apenas a chave 'text' de cada bloco
                    resposta_relatorio = "".join(
                        [
                            bloco.get("text", "")
                            for bloco in raw_content
                            if isinstance(bloco, dict)
                        ]
                    )
                else:
                    # Se já for string, apenas garante a tipagem
                    resposta_relatorio = str(raw_content)

                # Mostra o resultado na tela dentro de um container bonitinho
                st.success("Análise gerada com sucesso!")
                with st.expander("📄 Ver Relatório Consolidado", expanded=True):
                    st.markdown(resposta_relatorio)

            except Exception as e:
                st.error(f"Ocorreu um erro ao chamar a API do Gemini: {e}")

st.divider()

# 6. Tabela de Dados Brutos
st.markdown("#### Histórico de Interações")
st.markdown("Revise o que o aluno perguntou e como o agente respondeu.")

# CORREÇÃO 5: Usar .loc para o slice de colunas e passar os parâmetros posicionalmente no sort_values
colunas_desejadas = [
    "timestamp",
    "current_stage",
    "user_message",
    "bot_response",
    "approved",
    "thread_id",
]
tabela_exibicao = df.loc[:, colunas_desejadas]
tabela_exibicao = tabela_exibicao.sort_values("timestamp", ascending=False)

st.dataframe(tabela_exibicao, use_container_width=True, height=400, hide_index=True)

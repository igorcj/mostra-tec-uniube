import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(page_title="Mostra Tec - UNIUBE", page_icon="🔬", layout="wide")

# 2. Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Inicializar variáveis de controle de login no estado do Streamlit
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = ""
    st.session_state.perfil = ""

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔬 Mostra Tecnológica - UNIUBE")
    st.subheader("Acesso ao Sistema")
    
    with st.form("form_login"):
        user_input = st.text_input("Usuário:")
        pass_input = st.text_input("Senha:", type="password")
        botao_login = st.form_submit_button("Entrar")
        
    if botao_login:
        try:
            # Busca os usuários direto da aba 'Usuarios' da planilha (ttl=0 força buscar dado fresco)
            df_usuarios = conn.read(worksheet="Usuarios", ttl=0)
            
            # Valida se o usuário e senha existem combinados
            usuario_valido = df_usuarios[(df_usuarios['usuario'] == user_input) & (df_usuarios['senha'] == str(pass_input))]
            
            if not usuario_valido.empty:
                st.session_state.logado = True
                st.session_state.usuario = user_input
                st.session_state.perfil = usuario_valido.iloc[0]['perfil']
                st.rerun() # Reinicia o app já logado
            else:
                st.error("❌ Usuário ou senha incorretos.")
        except Exception as e:
            st.error(f"Erro ao conectar ao banco de dados dos usuários: {e}")

# --- SISTEMA LOGADO ---
else:
    # Barra lateral para Logout e Boas-vindas
    st.sidebar.title(f"👤 Olá, {st.session_state.usuario}!")
    st.sidebar.write(f"Perfil: **{st.session_state.perfil.upper()}**")
    if st.sidebar.button("Sair / Logout"):
        st.session_state.logado = False
        st.session_state.usuario = ""
        st.session_state.perfil = ""
        st.rerun()

    # -------------------------------------------------------------
    # PERFIL: AVALIADOR (Formulário de Lançamento de Notas)
    # -------------------------------------------------------------
    if st.session_state.perfil == "avaliador":
        st.title("📝 Lançamento de Notas")
        st.write("Selecione o trabalho e atribua as notas de acordo com os critérios.")
        
        # Dicionário de exemplo dos trabalhos (mude para os reais da UNIUBE)
        trabalhos = {
            "T01": "Análise da Água do Rio Uberaba",
            "T02": "Automação Residencial com Arduino",
            "T03": "Inteligência Artificial na Triagem Hospitalar",
            "T04": "Desenvolvimento de Concreto Sustentável"
        }
        
        with st.form(key="form_notas", clear_on_submit=True):
            id_trabalho = st.selectbox("Escolha o Trabalho:", options=list(trabalhos.keys()), format_func=lambda x: f"{x} - {trabalhos[x]}")
            
            st.divider()
            criterio_1 = st.slider("Inovação e Originalidade (0 a 10):", 0.0, 10.0, 5.0, step=0.5)
            criterio_2 = st.slider("Fundamentação Científica (0 a 10):", 0.0, 10.0, 5.0, step=0.5)
            criterio_3 = st.slider("Apresentação e Clareza (0 a 10):", 0.0, 10.0, 5.0, step=0.5)
            
            comentarios = st.text_area("Comentários / Justificativa (Opcional):")
            
            enviar_nota = st.form_submit_button("Submeter Avaliação")
            
        if enviar_nota:
            nota_final = round((criterio_1 + criterio_2 + criterio_3) / 3, 2)
            
            # Monta a linha para salvar
            nova_avaliacao = pd.DataFrame([{
                "ID": str(int(datetime.timestamp(datetime.now()))),
                "Avaliador": st.session_state.usuario,
                "ID_Trabalho": id_trabalho,
                "Titulo_Trabalho": trabalhos[id_trabalho],
                "Criterio_1": criterio_1,
                "Criterio_2": criterio_2,
                "Criterio_3": criterio_3,
                "Nota_Final": nota_final,
                "Comentarios": comentarios,
                "Data_Hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }])
            
            try:
                # Ler o que já tem, juntar e atualizar
                dados_atuais = conn.read(worksheet="Avaliacoes", ttl=0)
                dados_novos = pd.concat([dados_atuais, nova_avaliacao], ignore_index=True)
                conn.update(worksheet="Avaliacoes", data=dados_novos)
                
                st.success(f"✅ Sucesso! Nota {nota_final} enviada para o trabalho {id_trabalho}.")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao salvar na planilha: {e}")

    # -------------------------------------------------------------
    # PERFIL: ADMIN (Dashboard em Tempo Real)
    # -------------------------------------------------------------
    elif st.session_state.perfil == "admin":
        st.title("📊 Painel do Administrador - Tempo Real")
        st.write("Acompanhe o andamento das notas da feira de ciências.")
        
        try:
            # Carrega os dados reais das avaliações
            df_notas = conn.read(worksheet="Avaliacoes", ttl=0)
            
            if df_notas.empty or len(df_notas) == 0:
                st.warning("Ainda não foram enviadas avaliações pelos jurados.")
            else:
                # Converter notas para numérico por segurança
                df_notas["Nota_Final"] = pd.to_numeric(df_notas["Nota_Final"])
                
                # Indicadores rápidos (Métricas)
                total_avaliacoes = len(df_notas)
                trabalhos_avaliados = df_notas["ID_Trabalho"].nunique()
                media_geral = round(df_notas["Nota_Final"].mean(), 2)
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total de Notas Enviadas", total_avaliacoes)
                col2.metric("Trabalhos Avaliados", trabalhos_avaliados)
                col3.metric("Média Geral dos Trabalhos", media_geral)
                
                st.divider()
                
                # Gráfico do Ranking Geral (Média por trabalho)
                st.subheader("🏆 Ranking dos Trabalhos (Média das Notas)")
                ranking = df_notas.groupby(["ID_Trabalho", "Titulo_Trabalho"])["Nota_Final"].mean().reset_index()
                ranking = ranking.sort_values(by="Nota_Final", ascending=False)
                
                fig = px.bar(ranking, x="Nota_Final", y="Titulo_Trabalho", orientation='h',
                             text="Nota_Final", title="Melhores Avaliados",
                             labels={"Nota_Final": "Média", "Titulo_Trabalho": "Trabalho"},
                             color="Nota_Final", color_continuous_scale="Viridis")
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                
                st.divider()
                
                # Tabela de dados bruta para auditoria rápida se precisar
                st.subheader("📋 Histórico Completo de Votos")
                st.dataframe(df_notas.sort_values(by="Data_Hora", ascending=False), use_container_width=True)
                
        except Exception as e:
            st.error(f"Erro ao carregar o Dashboard: {e}")
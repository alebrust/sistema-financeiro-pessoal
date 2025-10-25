# --- ARQUIVO: app.py ---

import streamlit as st
from sistema_financeiro import GerenciadorContas, ContaCorrente, ContaInvestimento

# --- Configuração da Página ---
st.set_page_config(
    page_title="Meu Sistema Financeiro",
    page_icon="💰",
    layout="centered"
)

# --- Inicialização do Sistema ---
# O Streamlit não tem acesso ao Google Drive, então usaremos um arquivo local.
# O Streamlit Community Cloud cuidará de manter esse arquivo.
CAMINHO_ARQUIVO = "dados_contas.json"
gerenciador = GerenciadorContas(CAMINHO_ARQUIVO)

# Se for a primeira vez, cria dados de exemplo
if not gerenciador.contas:
    st.toast("Nenhum dado encontrado! Criando contas de exemplo...")
    gerenciador.adicionar_conta(ContaCorrente(nome="Conta Corrente Principal", saldo=2000, limite_cheque_especial=500))
    gerenciador.adicionar_conta(ContaInvestimento(nome="Ações - Longo Prazo", tipo_investimento="Renda Variável", saldo=10000))
    gerenciador.salvar_dados()

# --- Título da Aplicação ---
st.title("Meu Sistema de Gestão Financeira Pessoal 💰")
st.markdown("Bem-vindo ao seu painel de controle financeiro.")

# --- Exibição dos Saldos ---
st.header("Visão Geral das Contas")

contas = gerenciador.contas
if contas:
    # Cria uma lista de dicionários para exibir na tabela
    dados_tabela = [
        {
            "Conta": c.nome,
            "Tipo": c.__class__.__name__.replace("Conta", ""),
            "Saldo (R$)": f"{c.saldo:,.2f}"
        } 
        for c in contas
    ]
    st.table(dados_tabela)

    # Exibe o patrimônio total
    patrimonio_total = sum(c.saldo for c in contas)
    st.metric(label="**Patrimônio Total**", value=f"R$ {patrimonio_total:,.2f}")
else:
    st.warning("Nenhuma conta encontrada.")

# --- Funcionalidade de Transferência ---
st.header("Realizar Transferência")

if len(contas) >= 2:
    # Cria uma lista de nomes de contas para os menus de seleção
    nomes_contas = [c.nome for c in contas]
    
    # Usa colunas para organizar a interface
    col1, col2 = st.columns(2)
    with col1:
        conta_origem_nome = st.selectbox("De:", nomes_contas, key="origem")
    with col2:
        # Filtra a lista de destino para não incluir a origem
        opcoes_destino = [nome for nome in nomes_contas if nome != conta_origem_nome]
        conta_destino_nome = st.selectbox("Para:", opcoes_destino, key="destino")

    valor_transferencia = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")

    if st.button("Confirmar Transferência", use_container_width=True):
        # Encontra os IDs das contas selecionadas
        id_origem = next((c.id_conta for c in contas if c.nome == conta_origem_nome), None)
        id_destino = next((c.id_conta for c in contas if c.nome == conta_destino_nome), None)

        if id_origem and id_destino:
            sucesso = gerenciador.realizar_transferencia(id_origem, id_destino, valor_transferencia)
            if sucesso:
                st.success(f"Transferência de R${valor_transferencia:,.2f} realizada com sucesso!")
                gerenciador.salvar_dados()
                # Força a página a recarregar para mostrar os novos saldos
                st.rerun()
            else:
                st.error("Transferência falhou! Verifique se há saldo suficiente.")
        else:
            st.error("Erro ao encontrar as contas selecionadas.")
else:
    st.info("Você precisa de pelo menos duas contas para realizar uma transferência.")

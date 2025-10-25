# --- ARQUIVO: app.py (VERSÃO 11 - CORREÇÃO DA LIMPEZA DE FORMULÁRIO) ---

import streamlit as st
from sistema_financeiro import GerenciadorContas, ContaCorrente, ContaInvestimento

# --- Configuração da Página ---
st.set_page_config(page_title="Meu Sistema Financeiro", page_icon="💰", layout="wide")

# --- Inicialização do Sistema ---
if 'gerenciador' not in st.session_state:
    st.session_state.gerenciador = GerenciadorContas("dados_contas.json")
gerenciador = st.session_state.gerenciador

# --- Título da Aplicação ---
st.title("Meu Sistema de Gestão Financeira Pessoal 💰")

# --- Colunas Principais ---
col1, col2 = st.columns([1, 1])

# --- COLUNA DA ESQUERDA: Contas e Transferências ---
with col1:
    st.header("Painel de Contas")
    
    contas = gerenciador.contas
    if not contas:
        st.warning("Nenhuma conta encontrada. Adicione uma nova conta no painel ao lado.")
    
    for conta in contas:
        with st.expander(f"{conta.nome} - R$ {conta.saldo:,.2f}"):
            st.write(f"**Tipo:** {conta.__class__.__name__.replace('Conta', '')}")
            st.write(f"**ID:** `{conta.id_conta}`")
            
            with st.form(f"edit_form_{conta.id_conta}"):
                novo_nome = st.text_input("Novo nome da conta", value=conta.nome, key=f"edit_name_{conta.id_conta}")
                if st.form_submit_button("Salvar Alterações"):
                    if conta.editar_nome(novo_nome):
                        gerenciador.salvar_dados()
                        st.toast(f"Conta '{novo_nome}' atualizada!")
                        st.rerun()
            
            if st.button(f"Remover Conta '{conta.nome}'", key=f"remove_{conta.id_conta}", type="primary"):
                if gerenciador.remover_conta(conta.id_conta):
                    gerenciador.salvar_dados()
                    st.toast(f"Conta '{conta.nome}' removida!")
                    st.rerun()

    st.header("Realizar Transferência")
    if len(contas) >= 2:
        nomes_contas = [c.nome for c in contas]
        conta_origem_nome = st.selectbox("De:", nomes_contas, key="origem")
        opcoes_destino = [nome for nome in nomes_contas if nome != conta_origem_nome]
        conta_destino_nome = st.selectbox("Para:", opcoes_destino, key="destino")
        valor_transferencia = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
        if st.button("Confirmar Transferência", use_container_width=True):
            id_origem = next((c.id_conta for c in contas if c.nome == conta_origem_nome), None)
            id_destino = next((c.id_conta for c in contas if c.nome == conta_destino_nome), None)
            if id_origem and id_destino:
                if gerenciador.realizar_transferencia(id_origem, id_destino, valor_transferencia):
                    gerenciador.salvar_dados()
                    st.success("Transferência realizada com sucesso!")
                    st.rerun()
                else:
                    st.error("Falha na transferência. Saldo insuficiente?")
    else:
        st.info("Adicione pelo menos duas contas para realizar transferências.")

# --- COLUNA DA DIREITA: Ações e Resumo ---
with col2:
    st.header("Ações")
    # MUDANÇA IMPORTANTE: clear_on_submit=True
    with st.form("add_account_form", clear_on_submit=True):
        st.subheader("Adicionar Nova Conta")
        tipo_conta = st.selectbox("Tipo de Conta", ["Conta Corrente", "Conta Investimento"])
        nome_conta = st.text_input("Nome da Conta")
        saldo_inicial = st.number_input("Saldo Inicial (R$)", min_value=0.0, format="%.2f")
        
        if tipo_conta == "Conta Corrente":
            limite = st.number_input("Limite do Cheque Especial (R$)", min_value=0.0, format="%.2f")
        else:
            tipo_invest = st.text_input("Tipo de Investimento (Ex: Ações, Cripto)")

        # MUDANÇA IMPORTANTE: Removemos o on_click
        submitted_add = st.form_submit_button("Adicionar Conta")

        if submitted_add:
            if not nome_conta:
                st.error("O nome da conta é obrigatório.")
            else:
                nova_conta = None
                if tipo_conta == "Conta Corrente":
                    nova_conta = ContaCorrente(nome=nome_conta, saldo=saldo_inicial, limite_cheque_especial=limite)
                else:
                    if not tipo_invest:
                        st.error("O tipo de investimento é obrigatório.")
                    else:
                        nova_conta = ContaInvestimento(nome=nome_conta, saldo=saldo_inicial, tipo_investimento=tipo_invest)
                
                if nova_conta:
                    gerenciador.adicionar_conta(nova_conta)
                    gerenciador.salvar_dados()
                    st.success(f"Conta '{nome_conta}' adicionada com sucesso!")
                    # O st.rerun() não é mais estritamente necessário aqui, 
                    # pois o Streamlit já recarrega a página após a submissão do formulário.
                    # Mas podemos manter para garantir consistência.
                    st.rerun()

    st.header("Resumo Financeiro")
    if contas:
        patrimonio_total = sum(c.saldo for c in contas)
        st.metric(label="**Patrimônio Total**", value=f"R$ {patrimonio_total:,.2f}")
    else:
        st.metric(label="**Patrimônio Total**", value="R$ 0,00")

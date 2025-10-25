# --- ARQUIVO: app.py (VERSÃO 35 - CORREÇÃO FINAL DA REGRESSÃO DO FORMULÁRIO) ---

import streamlit as st
import pandas as pd
from datetime import datetime
from sistema_financeiro import GerenciadorContas, ContaCorrente, ContaInvestimento
from collections import defaultdict

# --- Configuração da Página ---
st.set_page_config(page_title="Meu Sistema Financeiro", page_icon="💰", layout="wide")

# --- Inicialização do Sistema ---
if 'gerenciador' not in st.session_state:
    st.session_state.gerenciador = GerenciadorContas("dados_v3.json")

# --- Título Principal ---
st.title("Meu Sistema de Gestão Financeira Pessoal 💰")

# --- ABAS PRINCIPAIS DA APLICAÇÃO ---
tab_dashboard, tab_transacoes, tab_contas = st.tabs(["📊 Dashboard", "📈 Histórico de Transações", "🏦 Contas"])

# --- ABA 1: DASHBOARD ---
with tab_dashboard:
    col1, col2 = st.columns([1, 1])
    with col2:
        st.header("Ações Rápidas")
        with st.expander("💸 Registrar Nova Transação", expanded=True):
            contas_disponiveis = st.session_state.gerenciador.contas
            if not contas_disponiveis:
                st.warning("Crie uma conta na aba 'Contas' para começar.")
            else:
                with st.form("new_transaction_form", clear_on_submit=True):
                    tipo_transacao = st.selectbox("Tipo", ["Receita", "Despesa"])
                    conta_selecionada_nome = st.selectbox("Conta", [c.nome for c in contas_disponiveis])
                    descricao = st.text_input("Descrição")
                    valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
                    data_transacao = st.date_input("Data", value=datetime.today())
                    submitted = st.form_submit_button("Registrar")
                    if submitted:
                        if not descricao: st.error("A descrição é obrigatória.")
                        else:
                            conta_id = next((c.id_conta for c in contas_disponiveis if c.nome == conta_selecionada_nome), None)
                            sucesso = st.session_state.gerenciador.registrar_transacao(id_conta=conta_id, descricao=descricao, valor=valor, tipo=tipo_transacao, data_transacao=data_transacao)
                            if sucesso:
                                st.session_state.gerenciador.salvar_dados(); st.success("Transação registrada!"); st.rerun()
                            else:
                                st.error("Falha ao registrar. Saldo insuficiente?")
        st.header("Resumo Financeiro")
        todas_as_contas = st.session_state.gerenciador.contas
        if todas_as_contas:
            saldos_agrupados = defaultdict(float)
            for conta in todas_as_contas:
                if isinstance(conta, ContaCorrente): saldos_agrupados["Contas Correntes"] += conta.saldo
                elif isinstance(conta, ContaInvestimento): saldos_agrupados[conta.tipo_investimento] += conta.saldo
            st.subheader("Patrimônio por Categoria")
            for categoria, saldo in saldos_agrupados.items(): st.metric(label=categoria, value=f"R$ {saldo:,.2f}")
            st.divider()
            patrimonio_total = sum(saldos_agrupados.values()); st.metric(label="**Patrimônio Total**", value=f"R$ {patrimonio_total:,.2f}")
        else:
            st.metric(label="**Patrimônio Total**", value="R$ 0,00")
    with col1:
        st.header("Realizar Transferência")
        todas_as_contas = st.session_state.gerenciador.contas
        if len(todas_as_contas) >= 2:
            with st.form("transfer_form", clear_on_submit=True):
                nomes_contas = [c.nome for c in todas_as_contas]
                col_form1, col_form2 = st.columns(2)
                with col_form1: conta_origem_nome = st.selectbox("De:", nomes_contas, key="transfer_origem")
                with col_form2:
                    opcoes_destino = [nome for nome in nomes_contas if nome != st.session_state.get("transfer_origem", nomes_contas[0])]
                    conta_destino_nome = st.selectbox("Para:", opcoes_destino, key="transfer_destino")
                valor_transferencia = st.number_input("Valor (R$)", min_value=0.01, format="%.2f", key="transfer_valor")
                submitted_transfer = st.form_submit_button("Confirmar Transferência", use_container_width=True)
                if submitted_transfer:
                    id_origem = next((c.id_conta for c in todas_as_contas if c.nome == conta_origem_nome), None)
                    id_destino = next((c.id_conta for c in todas_as_contas if c.nome == conta_destino_nome), None)
                    if id_origem and id_destino and valor_transferencia > 0:
                        if st.session_state.gerenciador.realizar_transferencia(id_origem, id_destino, valor_transferencia):
                            st.session_state.gerenciador.salvar_dados(); st.success("Transferência realizada!"); st.rerun()
                        else: st.error("Falha na transferência. Saldo insuficiente?")
                    else: st.error("Erro nos dados da transferência.")
        else:
            st.info("Adicione pelo menos duas contas para realizar transferências.")

# --- ABA 2: HISTÓRICO DE TRANSAÇÕES ---
with tab_transacoes:
    st.header("Histórico de Todas as Transações")
    transacoes = st.session_state.gerenciador.transacoes
    if not transacoes:
        st.info("Nenhuma transação registrada ainda.")
    else:
        mapa_contas = {c.id_conta: c.nome for c in st.session_state.gerenciador.contas}
        dados_df = []
        for t in sorted(transacoes, key=lambda x: x.data, reverse=True):
            dados_df.append({
                "Data": t.data.strftime("%d/%m/%Y"),
                "Conta": mapa_contas.get(t.id_conta, "Conta Removida"),
                "Descrição": t.descricao,
                "Tipo": t.tipo,
                "Valor (R$)": f"+{t.valor:,.2f}" if t.tipo == "Receita" else f"-{t.valor:,.2f}"
            })
        df = pd.DataFrame(dados_df)
        st.dataframe(df, use_container_width=True)

# --- ABA 3: GESTÃO DE CONTAS ---
with tab_contas:
    st.header("Gerenciar Contas")
    col_contas1, col_contas2 = st.columns(2)
    with col_contas2:
        # --- MUDANÇA FINAL E CORRETA AQUI ---
        with st.form("add_account_form", clear_on_submit=True):
            st.subheader("Adicionar Nova Conta")
            tipo_conta = st.selectbox("Tipo de Conta", ["Conta Corrente", "Conta Investimento"])
            nome_conta = st.text_input("Nome da Conta")
            logo_url_add = st.text_input("URL do Logo (Opcional)")
            saldo_inicial = st.number_input("Saldo Inicial (R$)", min_value=0.0, format="%.2f")
            
            st.markdown("---") # Divisor para clareza
            st.write("**Detalhes Específicos (preencha apenas o relevante):**")
            
            # Ambos os campos são sempre visíveis
            limite = st.number_input("Limite do Cheque Especial (para Contas Correntes)", min_value=0.0, format="%.2f")
            tipo_invest = st.text_input("Tipo de Investimento (para Contas de Investimento)")

            submitted_add = st.form_submit_button("Adicionar Conta", use_container_width=True)
            if submitted_add:
                if not nome_conta: st.error("O nome da conta é obrigatório.")
                else:
                    nova_conta = None
                    if tipo_conta == "Conta Corrente":
                        nova_conta = ContaCorrente(nome=nome_conta, saldo=saldo_inicial, limite_cheque_especial=limite, logo_url=logo_url_add)
                    else: # tipo_conta == "Conta Investimento"
                        if not tipo_invest:
                            st.error("O tipo de investimento é obrigatório para Contas de Investimento.")
                        else:
                            nova_conta = ContaInvestimento(nome=nome_conta, saldo=saldo_inicial, tipo_investimento=tipo_invest, logo_url=logo_url_add)
                    if nova_conta:
                        st.session_state.gerenciador.adicionar_conta(nova_conta); st.session_state.gerenciador.salvar_dados(); st.success(f"Conta '{nome_conta}' adicionada!"); st.rerun()
    
    with col_contas1:
        st.subheader("Contas Existentes")
        todas_as_contas = st.session_state.gerenciador.contas
        if not todas_as_contas: st.info("Nenhuma conta cadastrada.")
        for conta in todas_as_contas:
            logo_col, expander_col = st.columns([1, 6])
            with logo_col:
                if conta.logo_url: st.image(conta.logo_url, width=50)
                else: st.write("🏦") 
            with expander_col:
                with st.expander(f"{conta.nome} - R$ {conta.saldo:,.2f}"):
                    st.write(f"**Tipo:** {conta.__class__.__name__.replace('Conta', '')}")
                    if isinstance(conta, ContaCorrente): st.write(f"**Limite:** R$ {conta.limite_cheque_especial:,.2f}")
                    elif isinstance(conta, ContaInvestimento): st.write(f"**Tipo de Investimento:** {conta.tipo_investimento}")
                    st.divider()
                    with st.form(f"edit_form_{conta.id_conta}"):
                        novo_nome = st.text_input("Nome", value=conta.nome); nova_logo_url = st.text_input("URL do Logo", value=conta.logo_url)
                        if isinstance(conta, ContaCorrente): novo_limite = st.number_input("Limite", min_value=0.0, value=float(conta.limite_cheque_especial), format="%.2f")
                        elif isinstance(conta, ContaInvestimento): novo_tipo_invest = st.text_input("Tipo de Investimento", value=conta.tipo_investimento)
                        if st.form_submit_button("Salvar Alterações"):
                            nome_mudou = conta.editar_nome(novo_nome); logo_mudou = conta.editar_logo_url(nova_logo_url); attr_mudou = False
                            if isinstance(conta, ContaCorrente): attr_mudou = conta.editar_limite(novo_limite)
                            elif isinstance(conta, ContaInvestimento): attr_mudou = conta.editar_tipo_investimento(novo_tipo_invest)
                            if nome_mudou or logo_mudou or attr_mudou:
                                st.session_state.gerenciador.salvar_dados(); st.toast(f"Conta '{novo_nome}' atualizada!"); st.rerun()
                    if st.button(f"Remover Conta", key=f"remove_{conta.id_conta}", type="primary"):
                        if st.session_state.gerenciador.remover_conta(conta.id_conta):
                            st.session_state.gerenciador.salvar_dados(); st.toast(f"Conta '{conta.nome}' removida!"); st.rerun()
            st.write("")

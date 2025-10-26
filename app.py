# --- ARQUIVO: app.py (VERSÃO 42 - INTERFACE DE COMPRA DE ATIVOS) ---

import streamlit as st
import pandas as pd
from datetime import datetime
from sistema_financeiro import GerenciadorContas, ContaCorrente, ContaInvestimento, Ativo
from collections import defaultdict

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.set_page_config(page_title="Meu Sistema Financeiro", page_icon="💰", layout="wide")

if 'gerenciador' not in st.session_state:
    st.session_state.gerenciador = GerenciadorContas("dados_v5.json")

st.title("Meu Sistema de Gestão Financeira Pessoal 💰")

tab_dashboard, tab_transacoes, tab_contas = st.tabs(["📊 Dashboard", "📈 Histórico de Transações", "🏦 Contas"])

with tab_dashboard:
    col1, col2 = st.columns([1, 1])
    with col2:
        st.header("Ações Rápidas")

        # --- NOVO FORMULÁRIO DE COMPRA DE ATIVO ---
        with st.expander("📈 Comprar Ativo"):
            contas_correntes = [c for c in st.session_state.gerenciador.contas if isinstance(c, ContaCorrente)]
            contas_investimento = [c for c in st.session_state.gerenciador.contas if isinstance(c, ContaInvestimento)]

            if not contas_correntes or not contas_investimento:
                st.warning("Você precisa de pelo menos uma Conta Corrente (origem do dinheiro) e uma Conta de Investimento (corretora) para comprar um ativo.")
            else:
                with st.form("buy_asset_form", clear_on_submit=True):
                    st.write("**Registrar Compra de Ativo**")
                    
                    # Seleção de contas
                    conta_origem_nome = st.selectbox("Dinheiro saiu de:", [c.nome for c in contas_correntes])
                    conta_destino_nome = st.selectbox("Ativo custodiado em:", [c.nome for c in contas_investimento])
                    
                    # Detalhes do Ativo
                    ticker = st.text_input("Ticker do Ativo (ex: PETR4, AAPL)").upper()
                    tipo_ativo = st.selectbox("Tipo de Ativo", ["Ação BR", "FII", "Ação EUA", "Cripto", "Outro"])
                    
                    # Detalhes da Compra
                    col_qnt, col_preco = st.columns(2)
                    with col_qnt:
                        quantidade = st.number_input("Quantidade", min_value=0.000001, format="%.6f")
                    with col_preco:
                        preco_unitario = st.number_input("Preço por Unidade (R$)", min_value=0.01, format="%.2f")
                    
                    data_compra = st.date_input("Data da Compra", value=datetime.today(), format="DD/MM/YYYY")

                    submitted_buy = st.form_submit_button("Confirmar Compra")
                    if submitted_buy:
                        if not all([ticker, quantidade > 0, preco_unitario > 0]):
                            st.error("Preencha todos os detalhes da compra do ativo.")
                        else:
                            id_origem = next((c.id_conta for c in contas_correntes if c.nome == conta_origem_nome), None)
                            id_destino = next((c.id_conta for c in contas_investimento if c.nome == conta_destino_nome), None)
                            
                            sucesso = st.session_state.gerenciador.comprar_ativo(
                                id_conta_origem=id_origem,
                                id_conta_destino=id_destino,
                                ticker=ticker,
                                quantidade=quantidade,
                                preco_unitario=preco_unitario,
                                tipo_ativo=tipo_ativo,
                                data_compra=data_compra
                            )
                            if sucesso:
                                st.session_state.gerenciador.salvar_dados()
                                st.success(f"Compra de {ticker} registrada com sucesso!")
                                st.rerun()
                            else:
                                st.error("Falha na compra. Verifique o saldo da conta de origem.")

        with st.expander("💸 Registrar Nova Transação"):
            # ... (código de registrar transação sem mudanças)
            contas_disponiveis = [c for c in st.session_state.gerenciador.contas if isinstance(c, ContaCorrente)]
            if not contas_disponiveis:
                st.warning("Crie uma Conta Corrente na aba 'Contas' para registrar transações.")
            else:
                with st.form("new_transaction_form", clear_on_submit=True):
                    tipo_transacao = st.selectbox("Tipo", ["Receita", "Despesa"])
                    conta_selecionada_nome = st.selectbox("Conta", [c.nome for c in contas_disponiveis])
                    descricao = st.text_input("Descrição")
                    categoria = st.text_input("Categoria")
                    valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
                    data_transacao = st.date_input("Data", value=datetime.today(), format="DD/MM/YYYY")
                    if st.form_submit_button("Registrar"):
                        if not all([descricao, categoria]): st.error("Descrição e Categoria são obrigatórios.")
                        else:
                            conta_id = next((c.id_conta for c in contas_disponiveis if c.nome == conta_selecionada_nome), None)
                            sucesso = st.session_state.gerenciador.registrar_transacao(id_conta=conta_id, descricao=descricao, valor=valor, tipo=tipo_transacao, data_transacao=data_transacao, categoria=categoria)
                            if sucesso: st.session_state.gerenciador.salvar_dados(); st.success("Transação registrada!"); st.rerun()
                            else: st.error("Falha ao registrar. Saldo insuficiente?")
        
        st.header("Resumo Financeiro")
        # ... (código do resumo sem mudanças)
        todas_as_contas = st.session_state.gerenciador.contas
        if todas_as_contas:
            saldos_agrupados = defaultdict(float)
            for conta in todas_as_contas:
                if isinstance(conta, ContaCorrente): saldos_agrupados["Contas Correntes"] += conta.saldo
                elif isinstance(conta, ContaInvestimento):
                    for ativo in conta.ativos: saldos_agrupados[ativo.tipo_ativo] += ativo.valor_total
            st.subheader("Patrimônio por Categoria")
            for categoria, saldo in saldos_agrupados.items(): st.metric(label=categoria, value=formatar_moeda(saldo))
            st.divider()
            patrimonio_total = sum(c.saldo for c in todas_as_contas)
            st.metric(label="**Patrimônio Total**", value=formatar_moeda(patrimonio_total))
        else: st.metric(label="**Patrimônio Total**", value="R$ 0,00")

    with col1:
        st.header("Realizar Transferência")
        # ... (código de transferência sem mudanças)
        todas_as_contas = st.session_state.gerenciador.contas
        contas_para_transferencia = [c for c in todas_as_contas if isinstance(c, ContaCorrente)]
        if len(contas_para_transferencia) >= 1 and len(todas_as_contas) >= 2:
            with st.form("transfer_form", clear_on_submit=True):
                nomes_contas = [c.nome for c in todas_as_contas]
                nomes_contas_correntes = [c.nome for c in contas_para_transferencia]
                conta_origem_nome = st.selectbox("De (Conta Corrente):", nomes_contas_correntes, key="transfer_origem")
                opcoes_destino = [nome for nome in nomes_contas if nome != conta_origem_nome]
                conta_destino_nome = st.selectbox("Para:", opcoes_destino, key="transfer_destino")
                valor_transferencia = st.number_input("Valor (R$)", min_value=0.01, format="%.2f", key="transfer_valor")
                if st.form_submit_button("Confirmar Transferência", use_container_width=True):
                    id_origem = next((c.id_conta for c in todas_as_contas if c.nome == conta_origem_nome), None)
                    id_destino = next((c.id_conta for c in todas_as_contas if c.nome == conta_destino_nome), None)
                    if id_origem and id_destino and valor_transferencia > 0:
                        if st.session_state.gerenciador.realizar_transferencia(id_origem, id_destino, valor_transferencia):
                            st.session_state.gerenciador.salvar_dados(); st.success("Transferência realizada!"); st.rerun()
                        else: st.error("Falha na transferência. Saldo insuficiente?")
                    else: st.error("Erro nos dados da transferência.")
        else: st.info("Você precisa de pelo menos uma Conta Corrente e outra conta de destino para realizar transferências.")

# --- ABA 2: HISTÓRICO DE TRANSAÇÕES ---
with tab_transacoes:
    # ... (código do histórico sem mudanças)
    st.header("Histórico de Todas as Transações")
    transacoes = st.session_state.gerenciador.transacoes
    if not transacoes: st.info("Nenhuma transação registrada ainda.")
    else:
        mapa_contas = {c.id_conta: c.nome for c in st.session_state.gerenciador.contas}
        dados_df = [{"Data": t.data.strftime("%d/%m/%Y"), "Conta": mapa_contas.get(t.id_conta, "Conta Removida"), "Descrição": t.descricao, "Categoria": t.categoria, "Tipo": t.tipo, "Valor": formatar_moeda(t.valor) if t.tipo == "Receita" else f"-{formatar_moeda(t.valor)}"} for t in sorted(transacoes, key=lambda x: x.data, reverse=True)]
        df = pd.DataFrame(dados_df)
        st.dataframe(df, use_container_width=True, hide_index=True)

# --- ABA 3: GESTÃO DE CONTAS ---
with tab_contas:
    # ... (código de gestão de contas sem mudanças)
    st.header("Gerenciar Contas")
    col_contas1, col_contas2 = st.columns(2);
    with col_contas2:
        with st.form("add_account_form", clear_on_submit=True):
            st.subheader("Adicionar Nova Conta")
            tipo_conta = st.selectbox("Tipo de Conta", ["Conta Corrente", "Conta Investimento"])
            nome_conta = st.text_input("Nome da Conta")
            logo_url_add = st.text_input("URL do Logo (Opcional)")
            if tipo_conta == "Conta Corrente":
                saldo_inicial = st.number_input("Saldo Inicial (R$)", min_value=0.0, format="%.2f")
                limite = st.number_input("Limite do Cheque Especial (R$)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Adicionar Conta", use_container_width=True):
                if not nome_conta: st.error("O nome da conta é obrigatório.")
                else:
                    nova_conta = None
                    if tipo_conta == "Conta Corrente": nova_conta = ContaCorrente(nome=nome_conta, saldo=saldo_inicial, limite_cheque_especial=limite, logo_url=logo_url_add)
                    else: nova_conta = ContaInvestimento(nome=nome_conta, logo_url=logo_url_add)
                    if nova_conta: st.session_state.gerenciador.adicionar_conta(nova_conta); st.session_state.gerenciador.salvar_dados(); st.success(f"Conta '{nome_conta}' adicionada!"); st.rerun()
    with col_contas1:
        st.subheader("Contas Existentes")
        todas_as_contas = st.session_state.gerenciador.contas
        if not todas_as_contas: st.info("Nenhuma conta cadastrada.")
        else:
            tab_cc_ger, tab_ci_ger = st.tabs(["Contas Correntes", "Contas de Investimento"])
            with tab_cc_ger:
                contas_correntes = [c for c in todas_as_contas if isinstance(c, ContaCorrente)]
                if not contas_correntes: st.info("Nenhuma conta corrente cadastrada.")
                for conta in contas_correntes:
                    logo_col, expander_col = st.columns([1, 5]);
                    with logo_col:
                        if conta.logo_url: st.image(conta.logo_url, width=65)
                        else: st.write("🏦")
                    with expander_col:
                        with st.expander(f"{conta.nome} - {formatar_moeda(conta.saldo)}"):
                            st.write(f"**Limite:** {formatar_moeda(conta.limite_cheque_especial)}")
                            with st.form(f"edit_form_{conta.id_conta}"):
                                novo_nome = st.text_input("Nome", value=conta.nome); nova_logo_url = st.text_input("URL do Logo", value=conta.logo_url)
                                novo_limite = st.number_input("Limite", min_value=0.0, value=float(conta.limite_cheque_especial), format="%.2f")
                                if st.form_submit_button("Salvar Alterações"):
                                    nome_mudou = conta.editar_nome(novo_nome); logo_mudou = conta.editar_logo_url(nova_logo_url); attr_mudou = conta.editar_limite(novo_limite)
                                    if nome_mudou or logo_mudou or attr_mudou: st.session_state.gerenciador.salvar_dados(); st.toast(f"Conta '{novo_nome}' atualizada!"); st.rerun()
                            if st.button(f"Remover Conta", key=f"remove_{conta.id_conta}", type="primary"):
                                if st.session_state.gerenciador.remover_conta(conta.id_conta): st.session_state.gerenciador.salvar_dados(); st.toast(f"Conta '{conta.nome}' removida!"); st.rerun()
            with tab_ci_ger:
                contas_investimento = [c for c in todas_as_contas if isinstance(c, ContaInvestimento)]
                if not contas_investimento: st.info("Nenhuma conta de investimento cadastrada.")
                for conta in contas_investimento:
                    logo_col, expander_col = st.columns([1, 5])
                    with logo_col:
                        if conta.logo_url: st.image(conta.logo_url, width=65)
                        else: st.write("📈")
                    with expander_col:
                        with st.expander(f"{conta.nome} - {formatar_moeda(conta.saldo)}"):
                            st.write(f"**Patrimônio Consolidado:** {formatar_moeda(conta.saldo)}")
                            ativos_agrupados = defaultdict(float)
                            for ativo in conta.ativos: ativos_agrupados[ativo.tipo_ativo] += ativo.valor_total
                            if ativos_agrupados:
                                st.write("**Posição por Tipo de Ativo:**")
                                for tipo, subtotal in ativos_agrupados.items(): st.text(f"- {tipo}: {formatar_moeda(subtotal)}")
                            st.divider()
                            if not conta.ativos: st.info("Nenhum ativo nesta conta ainda.")
                            else:
                                st.write("**Ativos em Carteira:**")
                                df_ativos = pd.DataFrame([a.para_dict() for a in conta.ativos])
                                df_ativos["valor_total"] = df_ativos.apply(lambda row: formatar_moeda(row["quantidade"] * row["preco_medio"]), axis=1)
                                df_ativos["preco_medio"] = df_ativos["preco_medio"].apply(formatar_moeda)
                                st.dataframe(df_ativos[['ticker', 'quantidade', 'preco_medio', 'tipo_ativo', 'valor_total']], use_container_width=True, hide_index=True)
                            if st.button(f"Remover Corretora '{conta.nome}'", key=f"remove_{conta.id_conta}", type="primary"):
                                if st.session_state.gerenciador.remover_conta(conta.id_conta): st.session_state.gerenciador.salvar_dados(); st.toast(f"Conta '{conta.nome}' removida!"); st.rerun()

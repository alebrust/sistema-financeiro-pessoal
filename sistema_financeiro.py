# --- ARQUIVO: sistema_financeiro.py (VERSÃO 41 - ARQUITETURA DE PORTFÓLIO) ---

import json
from abc import ABC, abstractmethod
from uuid import uuid4
from datetime import date
from typing import List, Optional, Dict, Any

# --- NOVA CLASSE: Ativo ---
class Ativo:
    """Representa um único ativo dentro de uma conta de investimento."""
    def __init__(self, ticker: str, quantidade: float, preco_medio: float, tipo_ativo: str):
        if not all([ticker, tipo_ativo]) or quantidade <= 0 or preco_medio < 0:
            raise ValueError("Dados inválidos para o ativo.")
        
        self.ticker = ticker
        self.quantidade = quantidade
        self.preco_medio = preco_medio
        self.tipo_ativo = tipo_ativo # Ex: "Ação BR", "FII", "Ação EUA", "Cripto"

    @property
    def valor_total(self) -> float:
        """Calcula o valor total do ativo com base no preço médio de compra."""
        # No futuro, podemos substituir o preco_medio por uma cotação em tempo real.
        return self.quantidade * self.preco_medio

    def para_dict(self) -> Dict[str, Any]:
        """Converte o objeto para um dicionário para salvar em JSON."""
        return self.__dict__ # Retorna todos os atributos do objeto como um dicionário

# --- Classes Transacao e Conta (sem mudanças) ---
class Transacao:
    def __init__(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date, categoria: str, id_transacao: str = None):
        self.id_transacao = id_transacao if id_transacao else str(uuid4())
        self.id_conta, self.descricao, self.valor, self.tipo, self.data, self.categoria = id_conta, descricao, valor, tipo, data_transacao, categoria
    def para_dict(self) -> Dict[str, Any]:
        return {"id_transacao": self.id_transacao, "id_conta": self.id_conta, "descricao": self.descricao, "valor": self.valor, "tipo": self.tipo, "data": self.data.isoformat(), "categoria": self.categoria}

class Conta(ABC):
    def __init__(self, nome: str, saldo: float = 0.0, id_conta: str = None, logo_url: str = ""):
        self._id_conta, self._nome, self._saldo, self._logo_url = (id_conta if id_conta else str(uuid4()), nome, saldo, logo_url if logo_url else "")
    def alterar_saldo(self, valor: float): self._saldo += valor
    @property
    def logo_url(self) -> str: return self._logo_url
    def editar_logo_url(self, nova_url: str) -> bool:
        if isinstance(nova_url, str): self._logo_url = nova_url; return True
        return False
    def editar_nome(self, novo_nome: str) -> bool:
        if isinstance(novo_nome, str) and novo_nome.strip(): self._nome = novo_nome; return True
        return False
    @property
    def id_conta(self) -> str: return self._id_conta
    @property
    def nome(self) -> str: return self._nome
    @property
    def saldo(self) -> float: return self._saldo
    def depositar(self, valor: float):
        if not isinstance(valor, (int, float)) or valor <= 0: return
        self._saldo += valor
    @abstractmethod
    def sacar(self, valor: float) -> bool: pass
    def para_dict(self) -> Dict[str, Any]:
        return {"id_conta": self.id_conta, "tipo_classe": self.__class__.__name__, "nome": self.nome, "saldo": self.saldo, "logo_url": self.logo_url}
    def __repr__(self) -> str: return f"<{self.__class__.__name__}(nome='{self.nome}', saldo=R${self.saldo:.2f})>"

class ContaCorrente(Conta):
    def __init__(self, nome: str, saldo: float = 0.0, limite_cheque_especial: float = 0.0, **kwargs):
        super().__init__(nome, saldo, **kwargs)
        self._limite_cheque_especial = limite_cheque_especial
    def editar_limite(self, novo_limite: float) -> bool:
        if isinstance(novo_limite, (int, float)) and novo_limite >= 0: self._limite_cheque_especial = novo_limite; return True
        return False
    @property
    def limite_cheque_especial(self) -> float: return self._limite_cheque_especial
    @property
    def saldo_disponivel_saque(self) -> float: return self.saldo + self.limite_cheque_especial
    def sacar(self, valor: float) -> bool:
        if not isinstance(valor, (int, float)) or valor <= 0: return False
        if valor > self.saldo_disponivel_saque: return False
        self._saldo -= valor
        return True
    def para_dict(self) -> Dict[str, Any]:
        dados = super().para_dict(); dados["limite_cheque_especial"] = self.limite_cheque_especial; return dados

# --- MUDANÇA SIGNIFICATIVA: ContaInvestimento agora é uma carteira de ativos ---
class ContaInvestimento(Conta):
    def __init__(self, nome: str, **kwargs):
        # O saldo inicial é sempre 0. O valor vem dos ativos.
        super().__init__(nome, saldo=0.0, **kwargs) 
        self._ativos: List[Ativo] = []

    @property
    def saldo(self) -> float:
        """O saldo de uma conta de investimento é a soma do valor de seus ativos."""
        return sum(ativo.valor_total for ativo in self._ativos)

    @property
    def ativos(self) -> List[Ativo]:
        return self._ativos

    def adicionar_ativo(self, ativo: Ativo):
        """Adiciona um novo ativo à carteira."""
        self._ativos.append(ativo)

    # O método sacar é mantido para permitir transferências de "caixa" da corretora, se houver.
    # Por enquanto, vamos assumir que não há caixa e o saque não é permitido.
    def sacar(self, valor: float) -> bool:
        # No futuro, podemos implementar um 'saldo em caixa' na corretora.
        # Por agora, você não pode sacar diretamente de uma carteira de ativos.
        return False

    def para_dict(self) -> Dict[str, Any]:
        """Converte a conta e sua lista de ativos para um dicionário."""
        dados = super().para_dict()
        dados.pop('saldo', None) # Remove o saldo base, pois ele é calculado
        dados["ativos"] = [ativo.para_dict() for ativo in self._ativos]
        return dados

# --- MUDANÇAS NO GERENCIADOR PARA CARREGAR A NOVA ESTRUTURA ---
class GerenciadorContas:
    def __init__(self, arquivo_dados: str):
        self._contas: List[Conta] = []
        self._transacoes: List[Transacao] = []
        self._arquivo_dados = arquivo_dados
        self.carregar_dados()
    
    # ... (propriedades e métodos de transação sem mudanças)
    @property
    def contas(self) -> List[Conta]: return self._contas
    @property
    def transacoes(self) -> List[Transacao]: return self._transacoes
    def _apenas_registrar_transacao(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date, categoria: str):
        nova_transacao = Transacao(id_conta, descricao, valor, tipo, data_transacao, categoria)
        self._transacoes.append(nova_transacao)
    def registrar_transacao(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date, categoria: str) -> bool:
        conta = self.buscar_conta_por_id(id_conta)
        if not conta: return False
        valor_efetivo = valor if tipo == "Receita" else -valor
        if tipo == "Despesa":
            if isinstance(conta, ContaCorrente) and valor > conta.saldo_disponivel_saque: return False
            if isinstance(conta, ContaInvestimento) and valor > conta.saldo: return False
        conta.alterar_saldo(valor_efetivo)
        self._apenas_registrar_transacao(id_conta, descricao, valor, tipo, data_transacao, categoria)
        return True
    def realizar_transferencia(self, id_origem: str, id_destino: str, valor: float) -> bool:
        conta_origem = self.buscar_conta_por_id(id_origem)
        conta_destino = self.buscar_conta_por_id(id_destino)
        if not all([conta_origem, conta_destino]) or id_origem == id_destino or valor <= 0: return False
        if conta_origem.sacar(valor):
            conta_destino.depositar(valor)
            hoje = date.today()
            self._apenas_registrar_transacao(id_origem, f"Transferência para {conta_destino.nome}", valor, "Despesa", hoje, "Transferência")
            self._apenas_registrar_transacao(id_destino, f"Transferência de {conta_origem.nome}", valor, "Receita", hoje, "Transferência")
            return True
        return False
    
    def salvar_dados(self):
        dados_completos = {"contas": [c.para_dict() for c in self._contas], "transacoes": [t.para_dict() for t in self._transacoes]}
        with open(self._arquivo_dados, 'w', encoding='utf-8') as f: json.dump(dados_completos, f, indent=4, ensure_ascii=False)

    # MUDANÇA CRÍTICA: O método carregar_dados agora reconstrói os ativos
    def carregar_dados(self):
        try:
            with open(self._arquivo_dados, 'r', encoding='utf-8') as f: dados_completos = json.load(f)
            
            self._contas = []
            for dados_conta in dados_completos.get("contas", []):
                tipo_classe = dados_conta.pop("tipo_classe")
                
                if tipo_classe == "ContaCorrente":
                    self._contas.append(ContaCorrente(**dados_conta))
                
                elif tipo_classe == "ContaInvestimento":
                    # Recria a lista de ativos a partir dos dados do JSON
                    lista_ativos_dados = dados_conta.pop("ativos", [])
                    nova_conta_invest = ContaInvestimento(**dados_conta)
                    for dados_ativo in lista_ativos_dados:
                        novo_ativo = Ativo(**dados_ativo)
                        nova_conta_invest.adicionar_ativo(novo_ativo)
                    self._contas.append(nova_conta_invest)

            self._transacoes = []
            for dados_transacao in dados_completos.get("transacoes", []):
                dados_transacao["data_transacao"] = date.fromisoformat(dados_transacao.pop("data"))
                if "categoria" not in dados_transacao: dados_transacao["categoria"] = "Não categorizado"
                self._transacoes.append(Transacao(**dados_transacao))
        except (FileNotFoundError, json.JSONDecodeError):
            self._contas, self._transacoes = [], []
    
    # ... (outros métodos sem mudanças)
    def adicionar_conta(self, conta: Conta):
        if not isinstance(conta, Conta): return
        self._contas.append(conta)
    def buscar_conta_por_id(self, id_conta: str) -> Optional[Conta]:
        for conta in self._contas:
            if conta.id_conta == id_conta: return conta
        return None
    def remover_conta(self, id_conta: str) -> bool:
        conta_para_remover = self.buscar_conta_por_id(id_conta)
        if conta_para_remover:
            self._contas.remove(conta_para_remover)
            self._transacoes = [t for t in self._transacoes if t.id_conta != id_conta]
            return True
        return False

# --- ARQUIVO: sistema_financeiro.py (VERSÃO 37 - CORREÇÃO DO BUG DE DUPLICAÇÃO) ---

import json
from abc import ABC, abstractmethod
from uuid import uuid4
from datetime import date, datetime
from typing import List, Optional, Dict, Any

class Transacao:
    # ... (classe Transacao sem mudanças)
    def __init__(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date, id_transacao: str = None):
        if not all([id_conta, descricao, tipo]): raise ValueError("ID da conta, descrição e tipo são obrigatórios.")
        if tipo not in ["Receita", "Despesa"]: raise ValueError("Tipo de transação deve ser 'Receita' ou 'Despesa'.")
        self.id_transacao = id_transacao if id_transacao else str(uuid4())
        self.id_conta = id_conta
        self.descricao = descricao
        self.valor = valor
        self.tipo = tipo
        self.data = data_transacao
    def para_dict(self) -> Dict[str, Any]:
        return {"id_transacao": self.id_transacao, "id_conta": self.id_conta, "descricao": self.descricao, "valor": self.valor, "tipo": self.tipo, "data": self.data.isoformat()}

class Conta(ABC):
    # ... (classe Conta sem mudanças)
    def __init__(self, nome: str, saldo: float = 0.0, id_conta: str = None, logo_url: str = ""):
        self._id_conta = id_conta if id_conta else str(uuid4())
        self._nome = nome
        self._saldo = saldo
        self._logo_url = logo_url if logo_url else ""
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
    # ... (classe ContaCorrente sem mudanças)
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

class ContaInvestimento(Conta):
    # ... (classe ContaInvestimento sem mudanças)
    def __init__(self, nome: str, tipo_investimento: str, saldo: float = 0.0, **kwargs):
        super().__init__(nome, saldo, **kwargs)
        self._tipo_investimento = tipo_investimento
    def editar_tipo_investimento(self, novo_tipo: str) -> bool:
        if isinstance(novo_tipo, str) and novo_tipo.strip(): self._tipo_investimento = novo_tipo; return True
        return False
    @property
    def tipo_investimento(self) -> str: return self._tipo_investimento
    def sacar(self, valor: float) -> bool:
        if not isinstance(valor, (int, float)) or valor <= 0: return False
        if valor > self.saldo: return False
        self._saldo -= valor
        return True
    def para_dict(self) -> Dict[str, Any]:
        dados = super().para_dict(); dados["tipo_investimento"] = self.tipo_investimento; return dados

class GerenciadorContas:
    def __init__(self, arquivo_dados: str):
        self._contas: List[Conta] = []
        self._transacoes: List[Transacao] = []
        self._arquivo_dados = arquivo_dados
        self.carregar_dados()
    
    @property
    def contas(self) -> List[Conta]: return self._contas
    @property
    def transacoes(self) -> List[Transacao]: return self._transacoes

    def _apenas_registrar_transacao(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date):
        """Método privado que APENAS cria e salva o registro da transação, SEM alterar saldo."""
        nova_transacao = Transacao(id_conta, descricao, valor, tipo, data_transacao)
        self._transacoes.append(nova_transacao)

    def registrar_transacao(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date) -> bool:
        conta = self.buscar_conta_por_id(id_conta)
        if not conta: return False
        valor_efetivo = valor if tipo == "Receita" else -valor
        if tipo == "Despesa":
            if isinstance(conta, ContaCorrente) and valor > conta.saldo_disponivel_saque: return False
            if isinstance(conta, ContaInvestimento) and valor > conta.saldo: return False
        conta.alterar_saldo(valor_efetivo)
        self._apenas_registrar_transacao(id_conta, descricao, valor, tipo, data_transacao)
        return True

    def realizar_transferencia(self, id_origem: str, id_destino: str, valor: float) -> bool:
        conta_origem = self.buscar_conta_por_id(id_origem)
        conta_destino = self.buscar_conta_por_id(id_destino)
        if not all([conta_origem, conta_destino]) or id_origem == id_destino or valor <= 0: return False
        
        # A alteração de saldo acontece UMA VEZ aqui
        if conta_origem.sacar(valor):
            conta_destino.depositar(valor)
            
            # CORREÇÃO: Chamamos o método privado que SÓ registra, sem alterar o saldo de novo.
            hoje = date.today()
            self._apenas_registrar_transacao(id_origem, f"Transferência para {conta_destino.nome}", valor, "Despesa", hoje)
            self._apenas_registrar_transacao(id_destino, f"Transferência de {conta_origem.nome}", valor, "Receita", hoje)
            return True
        return False

    # ... (resto do Gerenciador sem mudanças)
    def salvar_dados(self):
        dados_completos = {"contas": [c.para_dict() for c in self._contas], "transacoes": [t.para_dict() for t in self._transacoes]}
        with open(self._arquivo_dados, 'w', encoding='utf-8') as f: json.dump(dados_completos, f, indent=4, ensure_ascii=False)
    def carregar_dados(self):
        try:
            with open(self._arquivo_dados, 'r', encoding='utf-8') as f: dados_completos = json.load(f)
            self._contas = []
            for dados_conta in dados_completos.get("contas", []):
                tipo_classe = dados_conta.pop("tipo_classe")
                if tipo_classe == "ContaCorrente": self._contas.append(ContaCorrente(**dados_conta))
                elif tipo_classe == "ContaInvestimento": self._contas.append(ContaInvestimento(**dados_conta))
            self._transacoes = []
            for dados_transacao in dados_completos.get("transacoes", []):
                dados_transacao["data_transacao"] = date.fromisoformat(dados_transacao.pop("data"))
                self._transacoes.append(Transacao(**dados_transacao))
        except (FileNotFoundError, json.JSONDecodeError): self._contas, self._transacoes = [], []
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

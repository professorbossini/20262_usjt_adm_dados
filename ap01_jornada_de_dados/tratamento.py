import matplotlib
matplotlib.use('Agg')
import pandas as pd
import matplotlib.pyplot as plt
import config

NOMES = {
  "Transaction ID": "id_transacao",
  "Item": "item",
  "Quantity": "quantidade",
  "Price Per Unit": "preco_unitario",
  "Total Spent": "total",
  "Payment Method": "forma_pagamento",
  "Location": "local",
  "Transaction Date": "data"
}

CAMPOS = list(NOMES.values())

PROBLEMAS = ["", "ERROR", "UNKNOWN"]
AUSENTES = PROBLEMAS + ["Não informado", "Não identificado"]

ITENS = {
  "Coffee": "Café", "Tea": "Chá", "Sandwich": "Sanduíche",
  "Salad": "Salada", "Cake": "Bolo", "Cookie": "Cookie",
  "Smoothie": "Smoothie", "Juice": "Suco"
}

PAGAMENTOS = {
  "Cash": "Dinheiro", "Credit Card": "Cartão de crédito",
  "Digital Wallet": "Carteira digital"
}

LOCAIS = {
  "In-store": "No local", "Takeaway": "Para viagem"
}

CARDAPIO = {
  "Café": 2.0, "Chá": 1.5, "Sanduíche": 4.0, "Salada": 5.0,
  "Bolo": 3.0, "Cookie": 1.0, "Smoothie": 4.0, "Suco": 3.0
}

PRECO_EXCLUSIVO = {
  1.0: "Cookie", 1.5: "Chá", 2.0: "Café", 5.0: "Salada"
}


def diagnosticar(df):
  ruim = df[CAMPOS].isna() | df[CAMPOS].isin(AUSENTES)
  completude = (1- ruim.mean()) * 100
  perfeitas = (~ruim.any(axis=1)).mean() * 100
  return completude, perfeitas

def mostrar_diagnostico(completude, perfeitas):
  for coluna, valor in completude.items():
    print(f"{coluna} {config.br(valor, 1)}%")
  print(f"Linhas perfeitas: {config.br(perfeitas, 1)}%")

def padronizar(bronze):
  df = bronze.rename(columns=NOMES)
  df[CAMPOS] = df[CAMPOS].replace(PROBLEMAS, pd.NA)
  for coluna in ["quantidade", "preco_unitario", "total"]:
    df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
  df["data"] = pd.to_datetime(
      df["data"],
      format="%Y-%m-%d",
      errors="coerce"
  )
  df["item"] = df["item"].map(ITENS)
  df["forma_pagamento"] = df["forma_pagamento"].map(PAGAMENTOS)
  df["local"] = df["local"].map(LOCAIS)
  return df

def recuperar(df):
  lacunas = df[CAMPOS].isna()
  for rodada in range(3):
    df["preco_unitario"] = df["preco_unitario"].fillna(
      df["item"].map(CARDAPIO)
    )
    df["preco_unitario"] = df["preco_unitario"].fillna(
      df["total"] / df["quantidade"] 
    )
    df["quantidade"] = df["quantidade"].fillna(
      df["total"] / df["preco_unitario"]
    )
    df["total"] = df["total"].fillna(
      df["quantidade"] * df["preco_unitario"]
    )
    df["item"] = df["item"].fillna(
      df["preco_unitario"].map(PRECO_EXCLUSIVO)
    )
  df["_recuperado"] = (lacunas & df[CAMPOS].notna()).any(axis=1)
  return lacunas.sum() - df[CAMPOS].isna().sum()

def tratar():
  bronze = pd.read_parquet(config.BRONZE / "vendas.parquet")
  antes, perfeitas_antes= diagnosticar(bronze.rename(columns=NOMES))
  print("Diagnóstico da camada bronze (valores utilizáveis):")
  mostrar_diagnostico(antes, perfeitas_antes)
  df = padronizar(bronze)
  lacunas = df[CAMPOS].isna().sum().sum()
  print(f'Lacunas após padronizar: {config.br(lacunas)}')
  recuperados = recuperar(df)
  print('Valores recuperados pelas regras de negócio')
  for coluna, n in recuperados[recuperados > 0].items():
    print(f'{coluna}: {config.br(n)}')

def separar_quarentena(df):
  # venda sem total ou sem data não segue a jornada
  retida = df['total'].isna() | df['data'].isna()
  quarentena = df[retida].copy()
  quarentena['motivo'] = "sem data"
  quarentena.loc[quarentena['total'].isna(), "motivo"] = "sem valor total"
  return df[~retida].copy(), quarentena

def completar(silver):
  # Ausência explícita é melhor que ausência silenciosa
  silver["item"] = silver["item"].fillna("Não identificado")
  silver["forma_pagamento"] = silver['forma_pagamento'].fillna(
    'Não informado'
  )
  silver["local"] = silver["local"].fillna("Não informado")
  silver["quantidade"] = silver["quantidade"].round().astype("Int64")
  return silver
if __name__ == "__main__":
  tratar()
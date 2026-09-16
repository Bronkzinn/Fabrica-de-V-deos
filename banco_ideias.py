import os
import sqlite3
from datetime import datetime

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PASTA_BASE, "banco_ideias.db")

def conectar_banco():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ideias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria TEXT NOT NULL,
        gancho TEXT NOT NULL UNIQUE,
        texto TEXT NOT NULL,
        tema TEXT NOT NULL,
        legenda TEXT NOT NULL,
        hashtags TEXT NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usado_em TIMESTAMP,
        vezes_usado INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    return conn

def obter_ideia_sqlite(categoria=None):
    """
    Retorna a melhor ideia disponível no SQLite.
    Prioriza ideias nunca usadas (usado_em IS NULL) e, em seguida, as usadas há mais tempo (usado_em ASC).
    Isso garante que NENHUM tema seja repetido com frequência.
    """
    conn = conectar_banco()
    cursor = conn.cursor()

    if categoria:
        query = """
        SELECT * FROM ideias 
        WHERE categoria = ? 
        ORDER BY usado_em IS NULL DESC, usado_em ASC, vezes_usado ASC 
        LIMIT 1
        """
        cursor.execute(query, (categoria,))
    else:
        query = """
        SELECT * FROM ideias 
        ORDER BY usado_em IS NULL DESC, usado_em ASC, vezes_usado ASC 
        LIMIT 1
        """
        cursor.execute(query)

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None

def marcar_ideia_como_usada(ideia_id_ou_gancho):
    """
    Marca a ideia como usada na data/hora atual e incrementa o contador vezes_usado.
    """
    conn = conectar_banco()
    cursor = conn.cursor()

    if isinstance(ideia_id_ou_gancho, int):
        cursor.execute("""
        UPDATE ideias 
        SET usado_em = CURRENT_TIMESTAMP, vezes_usado = vezes_usado + 1 
        WHERE id = ?
        """, (ideia_id_ou_gancho,))
    else:
        cursor.execute("""
        UPDATE ideias 
        SET usado_em = CURRENT_TIMESTAMP, vezes_usado = vezes_usado + 1 
        WHERE gancho = ?
        """, (ideia_id_ou_gancho,))

    conn.commit()
    conn.close()

def obter_historico_exclusao_sqlite(limite=30):
    """
    Retorna uma lista dos últimos ganchos/temas usados para alimentar a trava de exclusão da IA.
    """
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT gancho FROM ideias 
    WHERE usado_em IS NOT NULL 
    ORDER BY usado_em DESC 
    LIMIT ?
    """, (limite,))

    rows = cursor.fetchall()
    conn.close()
    return [row["gancho"] for row in rows]

if __name__ == "__main__":
    ideia = obter_ideia_sqlite()
    if ideia:
        print(f"[+] Ideia selecionada do banco SQLite: {ideia['gancho']}")
        print(f"    Tema Pexels: {ideia['tema']}")
    else:
        print("[-] Nenhuma ideia encontrada no banco.")


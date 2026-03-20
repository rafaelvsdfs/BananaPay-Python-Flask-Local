import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

# Cria tabela de clientes
cursor.execute("""
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cpf TEXT NOT NULL UNIQUE
)
""")

# Cria tabela de contas
cursor.execute("""
CREATE TABLE IF NOT EXISTS contas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,
    saldo REAL DEFAULT 0,
    limite REAL DEFAULT 0,
    FOREIGN KEY(cliente_id) REFERENCES clientes(id)
)
""")

# Cria tabela de transações
cursor.execute("""
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,        -- 'deposito', 'saque', 'transferencia'
    valor REAL NOT NULL,
    destinatario_id INTEGER,   -- NULL se não houver
    data TEXT DEFAULT CURRENT_TIMESTAMP
)
""")


conn.commit()
conn.close()
print("Banco criado com sucesso")
import sqlite3

def get_conexao():
    conn = sqlite3.connect("banco.db", timeout=10)
    conn.row_factory = sqlite3.Row
    return conn
import mysql.connector
from config import *

# função para conectar ao banco
def conectar_db():
    conexao = mysql.connector.connect(
        host = DB_HOST,
        user = DB_USER,
        password = DB_PASSWORD,
        database = DB_NAME
    )
    cursor = conexao.cursor(dictionary=True) #agente que vai executando as tarefas
    return conexao, cursor

# função para desconectar do banco
def encerrar_db(cursor, conexao):
    cursor.close()
    conexao.close()

def limpar_input(campo):
    campolimpo = campo.replace(".","").replace("/","").replace("-","").replace(" ","").replace("(","").replace(" ","").replace(")","").replace("R$","")
    return campolimpo
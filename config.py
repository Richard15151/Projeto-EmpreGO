ambiente = 'desenvolvimento'

if ambiente == 'desenvolvimento':
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = 'senai'
    DB_NAME = 'emprego'

# config chave secreta (session)
SECRET_KEY = 'emprego'

# config de sessão
MASTER_EMAIL = 'adm@adm'
MASTER_PASSWORD = 'adm'
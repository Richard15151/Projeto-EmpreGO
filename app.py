from flask import Flask, render_template, request, redirect, session, send_from_directory
from db_functions import * #Importa funções do db_functions
from config import * #Config.py
from mysql.connector import Error #puxa a classe Error para lidar com erros de conexão do DB
import time
import os

app=Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = 'uploads/'

# rota da página inicial(todos tem acesso)
@app.route ('/')
def index():
    if session:
        if 'adm' in session:
            login = 'adm'
        else:
            login = 'empresa'
    else:
        login = False
    try:
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa 
        FROM vaga 
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa
        WHERE vaga.status = 'ativa'
        ORDER BY vaga.id_vaga DESC;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL)
        vagas = cursor.fetchall()
        return render_template('index.html', vagas=vagas, login=login)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

#Rota para a página de login com GET e POST
@app.route('/login', methods=['GET','POST'])
def login():
    #Se ja tiver uma sessão ativa e for o adm, ja manda pra rota do adm 
    if session:
        if 'adm' in session:
            return redirect('/adm')
        else:
            return redirect ('/empresa')

    if request.method == 'GET':
        return render_template('login.html', page='login')

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        #Ver se os campos de login estão vazios (Validação de login)
        if not email or not senha:
            erro = "Preencha todos os campos!"
            return render_template('login.html', msg_erro=erro)

        #verificar se é o adm que está acessando
        if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
            session['adm'] = True #criando a sessão do ADM
            return redirect('/adm')

        #NÃO É O ADM, IREMOS VER SE É UMA EMPRESA
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM empresa WHERE email=%s AND senha=%s'
            cursor.execute(comandoSQL, (email, senha))
            empresa_encontrada = cursor.fetchone()
            print(email)
            print(senha)
            print(empresa_encontrada)


        #EMPRESA NÃO ENCONTRADA
            if not empresa_encontrada:
                erro = "email e/ou senha incorretos"
                return render_template('login.html', msg_erro=erro)
        
        #EMPRESA ENCONTRADA, PORÉM INATIVA
            if empresa_encontrada['status'] == 'inativa':
                erro = "Sua empresa está inativa, entre em contato com o suporte"
                return render_template('login.html', msg_erro=erro)

        #EMPRESA ENCONTRADA E ATIVA
            session ['id_empresa'] = empresa_encontrada['id_empresa'] #SALVANDO ID DA EMPRESA
            session ['nome_empresa'] = empresa_encontrada['nome_empresa'] #SALVANDO NOME DA EMPRESA
            return redirect('/empresa')

        except Error as erro:
            return f"Erro de DB: {erro}"
        except Exception as erro:
            return f"Erro de BackEnd: {erro}"
        finally: encerrar_db(cursor, conexao)

#Rota do adm 
@app.route('/adm')
def adm():
  #Se não houver sessão ativa
    if not session:
        return redirect('/login')
    #Se não for o administrador
    if not 'adm' in session:
        return redirect('/empresa')
    try:
        conexao, cursor = conectar_db()
        comandoSQL ="SELECT * FROM empresa WHERE status = 'ativa'"
        #Selecione todos os campos da tabela empresa onde o campo status seja ativa
        cursor.execute(comandoSQL)
        empresas_ativas = cursor.fetchall() #transforma as empresas ativas em uma lista.
        comandoSQL ="SELECT * FROM empresa WHERE status = 'inativa'"
        cursor.execute(comandoSQL)
        empresas_inativas = cursor.fetchall()
        return render_template('adm.html', empresas_ativas=empresas_ativas, empresas_inativas=empresas_inativas)
    except Error as erro:
        return f"Erro de DB: {erro}"
    except Exception as erro:
        return f"Erro de BackEnd: {erro}"
    finally: encerrar_db(cursor, conexao)

#ROTA PARA ABRIR E RECEBER AS INFORMAÇÕES DE UMA NOVA EMPRESA
@app.route ('/cadastrar_empresa', methods=['POST','GET'])
def cadastrar_empresa():
    #Verifica se tem sessão
    if not session:
        return redirect('/login')
    #Se não é o adm que está acessando, se não for adm, deve ser alguma empresa
    if not 'adm' in session:
        return redirect('/empresa')
    # ACESSO AO FORMULÁRIO DE CADASTRO
    if request.method == 'GET':
        return render_template('cadastrar_empresa.html')

    # TRATANDO OS DADOS VINDOS DO FORMULÁRIO
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input(request.form['cnpj'])
        telefone = limpar_input(request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha'].strip()
    
    # if que verifica se tem algum dado vazio
    if not nome_empresa or not cnpj or not telefone or not email or not senha:
        return render_template('cadastrar_empresa.html', msg_erro="Preencha todos os campos!")
    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'INSERT INTO empresa (nome_empresa, cnpj, telefone, email, senha) VALUES (%s,%s,%s,%s,%s)'
        #%s evita falhas de SQL injection, onde ele é um especificador de formato.
        cursor.execute(comandoSQL, (nome_empresa, cnpj, telefone, email, senha))
        conexao.commit()#comandos dml (insert, update, delete) atualizam e editam dados no mysql, precisam do commit para confirma estas mudanças. SELECT não é dml e não precisa do commit.
        # return redirect('/adm')
        return render_template('concluido.html')
    except Error as erro:
        if erro.errno == 1062: # erro de duplicidade de chave primária, cadastrar algo único duas vezes.
            return render_template('cadastrar_empresa.html', msg_erro="Esse email já existe!")
        else:
            return f"Erro de DB: {erro}"
    except Exception as error:
        return f"Erro de BackEnd: {error}"
    finally:
        encerrar_db(cursor, conexao)

#ROTA PARA EDITAR EMPRESA
@app.route('/editar_empresa/<int:id_empresa>', methods=['GET','POST'])
def editar_empresa(id_empresa):

    if not session:
        return redirect('/login')
    
    if not session['adm']:
        return redirect('/login')
        
    if request.method == 'GET':
        try:
            conexao, cursor = conectar_db()
            comandosSQL = 'SELECT * FROM empresa WHERE id_empresa = %s'
            cursor.execute(comandosSQL, (id_empresa,))
            empresa = cursor.fetchone()
            return render_template('editar_empresa.html', empresa=empresa)
        except Error as erro:
            return f"Erro de DB: {erro}"
        except Exception as error:
            return f"Erro de BackEnd: {error}"
        finally:
            encerrar_db(cursor, conexao)

     # TRATANDO OS DADOS VINDOS DO FORMULÁRIO
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input(request.form['cnpj'])
        telefone = limpar_input(request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha']
        
    # if que verifica se tem algum dado vazio
    if not nome_empresa or not cnpj or not telefone or not email or not senha:
        return render_template('cadastrar_empresa.html', msg_erro="Preencha todos os campos!")
    try:
        conexao, cursor = conectar_db()
        comandoSQL = '''
        UPDATE empresa
        SET 
        nome_empresa=%s, cnpj=%s, telefone=%s, email=%s, senha=%s
        WHERE id_empresa = %s;
        '''
        cursor.execute(comandoSQL, (nome_empresa, cnpj, telefone, email, senha, id_empresa))
        conexao.commit()
        return render_template('concluido.html')
    except Error as erro:
        if erro.errno == 1062:
            return render_template('editar_empresa.html', msg_erro="Esse email já existe!")
        else:
            return f"Erro de DB: {erro}"
    except Exception as error:
        return f"Erro de BackEnd: {error}"
    finally:
        encerrar_db(cursor, conexao)

#ROTA PARA ATIVAR E DESATIVAR EMPRESA
@app.route('/status_empresa/<int:id_empresa>') #padrão sempre é GET
def status_empresa(id_empresa):
    if not session:
        return redirect('/login')
    
    if not session['adm']:
        return redirect('/login')
    
    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT status FROM empresa WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        status_empresa = cursor.fetchone()

        if status_empresa['status'] == 'ativa':
            novo_status = 'inativa'
        else:
            novo_status = 'ativa'
        
        comandoSQL = 'UPDATE empresa SET status = %s WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (novo_status, id_empresa))
        conexao.commit()

        # SE A EMPRESA ESTIVER SENDO DESATIVADA, AS VAGAS TAMBÉM SERÃO
        if novo_status == 'inativa':
            comandoSQL = 'UPDATE vaga SET status= %s WHERE id_empresa =%s'
            cursor.execute(comandoSQL,(novo_status,id_empresa))
            conexao.commit()
        return redirect ('/adm')

    except Error as erro:
        return f"Erro de DB: {erro}"
    except Exception as erro:
        return f"Erro de BackEnd: {erro}"
    finally: 
        encerrar_db(cursor, conexao)

# ROTA PARA EXCLUIR UMA EMPRESA
@app.route ('/excluir_empresa/<int:id_empresa>')
def excluir_empresa(id_empresa):
    if not session:
        return redirect('/login')
    
    if not session ['adm']:
        return redirect ('/login')
    
    try:
        conexao, cursor = conectar_db()
        # EXCLUINDO VAGAS RELACIONADAS DA EMPRESA EXCLUIDA
        comandoSQL = 'DELETE FROM vaga WHERE id_empresa=%s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()
        # EXCLUIR CADASTRO DA EMPRESA:
        comandoSQL = 'DELETE FROM empresa WHERE id_empresa=%s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()
        return redirect ('/adm')
    except Error as erro:
        return f"Erro de DB: {erro}"
    except Exception as erro:
        return f"Erro de BackEnd: {erro}"
    finally: 
        encerrar_db(cursor, conexao)

#ROTA PÁGINA DA EMPRESA
@app.route ('/empresa')
def empresa():
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    id_empresa = session['id_empresa']
    nome_empresa = session['nome_empresa']

    try:
        conexao, cursor = conectar_db()

        comandoSQL = "SELECT * FROM vaga WHERE id_empresa=%s AND status='ativa' ORDER BY id_vaga DESC"
        cursor.execute(comandoSQL,(id_empresa,))
        vagas_ativas = cursor.fetchall()

        comandoSQL = "SELECT * FROM vaga WHERE id_empresa=%s AND status='inativa' ORDER BY id_vaga DESC"
        cursor.execute(comandoSQL,(id_empresa,))
        vagas_inativas = cursor.fetchall()

        return render_template('empresa.html', nome_empresa=nome_empresa, vagas_ativas=vagas_ativas, vagas_inativas=vagas_inativas)
        vagas_inativas = vagas_inativas, nome_empresa= nome_empresa


    except Error as erro:
        return f"Erro de DB: {erro}"
    except Exception as erro:
        return f"Erro de BackEnd: {erro}"
    finally: 
        encerrar_db(cursor, conexao)

#ROTA PARA CADASTRAR VAGA
@app.route('/cadastrar_vaga', methods=['POST','GET'])
def cadastrar_vaga():
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')
    
    if request.method == 'GET':
        return render_template('cadastrar_vaga.html')
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        formato = request.form['formato']
        tipo = request.form['tipo']
        local = ''
        local = request.form['local']
        salario = ''
        salario = limpar_input(request.form['salario'])
        id_empresa = session['id_empresa']

        if not titulo or not descricao or not formato or not tipo:
            return render_template('cadastrar_vaga.html', msg_erro="Os campos obrigatórios precisam estar preenchidos!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            INSERT INTO Vaga (titulo, descricao, formato, tipo, local, salario, id_empresa)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(comandoSQL, (titulo, descricao, formato, tipo, local, salario, id_empresa))
            conexao.commit()
            return render_template('concluido.html')
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

#ROTA PARA EDITAR A VAGA
@app.route('/editar_vaga/<int:id_vaga>', methods=['GET','POST'])
def editar_vaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    if request.method == 'GET':
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM vaga WHERE id_vaga = %s;'
            cursor.execute(comandoSQL, (id_vaga,))
            vaga = cursor.fetchone()
            return render_template('editar_vaga.html', vaga=vaga)
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        formato = request.form['formato']
        tipo = request.form['tipo']
        local = request.form['local']
        salario = limpar_input(request.form['salario'])

        if not titulo or not descricao or not formato or not tipo:
            return redirect('/empresa')
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            UPDATE vaga SET titulo=%s, descricao=%s, formato=%s, tipo=%s, local=%s, salario=%s
            WHERE id_vaga = %s;
            '''
            cursor.execute(comandoSQL, (titulo, descricao, formato, tipo, local, salario, id_vaga))
            conexao.commit()
            return render_template('concluido.html')
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

#ROTA PARA ALTERAR O STATUS DA VAGA
@app.route("/status_vaga/<int:id_vaga>")
def status_vaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT status FROM vaga WHERE id_vaga = %s;'
        cursor.execute(comandoSQL, (id_vaga,))
        vaga = cursor.fetchone()
        if vaga['status'] == 'ativa':
            status = 'inativa'
        else:
            status = 'ativa'

        comandoSQL = 'UPDATE vaga SET status = %s WHERE id_vaga = %s'
        cursor.execute(comandoSQL, (status, id_vaga))
        conexao.commit()
        return redirect('/empresa')
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

#ROTA PARA EXCLUIR VAGA
@app.route("/excluir_vaga/<int:id_vaga>")
def excluir_vaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()
        #DELETANDO CURRICULOS DA VAGA
        comandoSQL = 'DELETE FROM candidato WHERE id_vaga = %s'
        cursor.execute(comandoSQL, (id_vaga,))
        conexao.commit()
        #DELETANDO A VAGA
        comandoSQL = 'DELETE FROM vaga WHERE id_vaga = %s AND status = "inativa"'
        cursor.execute(comandoSQL, (id_vaga,))
        conexao.commit()
        return redirect('/empresa')
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

#ROTA PARA VER DETALHES DA VAGA
@app.route('/sobre_vaga/<int:id_vaga>')
def sobre_vaga(id_vaga):
    try:
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa 
        FROM vaga 
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa 
        WHERE vaga.id_vaga = %s;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL, (id_vaga,))
        vaga = cursor.fetchone()
        
        if not vaga:
            return redirect('/')
        
        return render_template('sobre_vaga.html', vaga=vaga)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

# ROTA DE CANDIDATAR-SE
@app.route('/candidatar/<int:id_vaga>', methods=['GET', 'POST'])
def candidatar(id_vaga):
    if request.method == 'GET':
        return render_template('candidatar.html', id_vaga=id_vaga)

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = limpar_input(request.form['telefone'])
        curriculo = request.files['file']

        if not nome or not email or not telefone or not curriculo.filename:
            render_template('candidatar.html',msg_erro="Os campos obrigatórios precisam ser preenchidos")

        try:
            timestamp = int(time.time()) #CARIMBO BASEADO NOS MILISEGUNDOS PARA SEPARAR OS NOMES DOS ARQUIVOS
            nome_curriculo = f"{timestamp}_{id_vaga}_{curriculo.filename}"
            curriculo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_curriculo))
            conexao, cursor = conectar_db()
            comandoSQL = '''
            INSERT INTO candidato (nome, email, telefone, curriculo, id_vaga) 
            VALUES (%s, %s, %s, %s, %s)
            '''
            cursor.execute(comandoSQL, (nome, email, telefone, nome_curriculo, id_vaga,))
            conexao.commit()
            return render_template('concluido.html')

        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

@app.route('/ver_candidatos/<int:id_vaga>')
def ver_candidatos(id_vaga):
    if not session:
        return redirect('/login')
    if 'adm' in session:
        return redirect('/empresa')
    
    if request.method == 'GET':
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM candidato WHERE id_vaga = %s;'
            cursor.execute(comandoSQL, (id_vaga,))
            candidatos = cursor.fetchall()
            return render_template('candidatos.html', candidatos=candidatos)

        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/delete/<filename>')
def delete_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.remove(file_path)  # Exclui o arquivo

        conexao, cursor = conectar_db()
        comandoSQL = "DELETE FROM candidato WHERE curriculo = %s"
        cursor.execute(comandoSQL, (filename,))
        conexao.commit()

        return render_template('concluido.html')
    except mysql.connector.Error as erro:
        return f"Erro de banco de Dados: {erro}"
    except Exception as erro:
        return f"Erro de back-end: {erro}"
    finally:
        encerrar_db(conexao, cursor)

@app.route('/pesquisar', methods=['GET'])
def pesquisar():
    palavra_chave = request.args.get('q','')
    try:
        conexao, cursor = conectar_db()
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa
        FROM vaga
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa
        WHERE vaga.status = 'ativa' AND (
        vaga.titulo LIKE %s OR
        vaga.descricao LIKE %s
        )
        '''
        cursor.execute(comandoSQL, (f'%{palavra_chave}%', f'%{palavra_chave}%'))
        vagas = cursor.fetchall()
        return render_template('resultado_pesquisa.html', vagas=vagas, palavra_chave=palavra_chave)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

#Rota de logout:
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.errorhandler(404)
def not_found(error):
    return render_template('erro404.html'), 404

#Final do código
if __name__ == '__main__':
    app.run(debug=True)

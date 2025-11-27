from camada_dados.db_config import conectar_banco
from modelos.usuario import Aluno, Funcionario, Admin
import psycopg2.extras


class AlunoDao:
    def salvar(self, aluno: Aluno):
        return UsuarioDAO().salvar(aluno) 


class UsuarioDAO:
    def salvar(self, usuario):
        conexao = conectar_banco()
        if not conexao:
            return False
        cursor = conexao.cursor()
        try:
            # Inserção na tabela base
            sql_usuario = """
                INSERT INTO usuario (cpf, nome, email, senha, data_nasc, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_usuario, (usuario.cpf, usuario.nome, usuario.email,
                                         usuario.senha, usuario.data_nasc, usuario.status))

            # Tipo: aluno, funcionario ou admin
            if usuario.tipo == "aluno":
                sql_aluno = """
                    INSERT INTO aluno (cpf, matricula, curso, ano_inicio, categoria, valor_remuneracao,
                                       carga_horaria, horario_inicio, horario_fim, id_supervisor_servidor)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """
                valores = (usuario.cpf, usuario.matricula, usuario.curso, usuario.ano_inicio,
                           usuario.categoria, usuario.valor_remuneracao, usuario.carga_horaria,
                           usuario.horario_inicio, usuario.horario_fim, usuario.id_supervisor_servidor)
                cursor.execute(sql_aluno, valores)

            elif usuario.tipo in ["funcionario", "admin"]:
                # Primeiro salva como servidor
                sql_servidor = """
                    INSERT INTO servidor (cpf, id_servidor, data_admissao)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(sql_servidor, (usuario.cpf, usuario.id_servidor, usuario.data_admissao))

                if usuario.tipo == "funcionario":
                    cursor.execute("INSERT INTO funcionario (cpf, departamento, cargo) VALUES (%s,%s,%s)",
                                   (usuario.cpf, usuario.departamento, usuario.cargo))
                elif usuario.tipo == "admin":
                    cursor.execute("""
                        INSERT INTO admin (cpf, nivel_acesso, area_responsabilidade, data_ultimo_login)
                        VALUES (%s, %s, %s, %s)
                    """, (usuario.cpf, usuario.nivel_acesso,
                          usuario.area_responsabilidade, usuario.data_ultimo_login))

            conexao.commit()
            print("Usuário salvo com sucesso!")
            return True

        except Exception as e:
            conexao.rollback()
            print(f"Erro ao salvar usuário: {e}")
            return False
        finally:
            cursor.close()
            conexao.close()

    def buscar_por_cpf(self, cpf):
        conexao = conectar_banco()
        if not conexao:
            return None
        cursor = conexao.cursor()
        try:
            cursor.execute("SELECT * FROM usuario WHERE cpf = %s", (cpf,))
            u = cursor.fetchone()
            if not u:
                return None

            cpf, nome, email, senha, data_nasc, status = u

            # Tenta descobrir tipo
            cursor.execute("SELECT * FROM aluno WHERE cpf = %s", (cpf,))
            aluno = cursor.fetchone()
            if aluno:
                return Aluno(*u[:5], matricula=aluno[1], curso=aluno[2], ano_inicio=aluno[3],
                             categoria=aluno[4], valor_remuneracao=aluno[5], carga_horaria=aluno[6],
                             horario_inicio=aluno[7], horario_fim=aluno[8], id_supervisor_servidor=aluno[9])

            cursor.execute("SELECT * FROM admin WHERE cpf = %s", (cpf,))
            admin = cursor.fetchone()
            if admin:
                cursor.execute("SELECT id_servidor, data_admissao FROM servidor WHERE cpf = %s", (cpf,))
                serv = cursor.fetchone()
                return Admin(cpf, nome, email, senha, data_nasc,
                             id_servidor=serv[0], data_admissao=serv[1],
                             nivel_acesso=admin[1], area_responsabilidade=admin[2], data_ultimo_login=admin[3])

            cursor.execute("SELECT * FROM funcionario WHERE cpf = %s", (cpf,))
            func = cursor.fetchone()
            if func:
                cursor.execute("SELECT id_servidor, data_admissao FROM servidor WHERE cpf = %s", (cpf,))
                serv = cursor.fetchone()
                return Funcionario(cpf, nome, email, senha, data_nasc,
                                   id_servidor=serv[0], data_admissao=serv[1],
                                   departamento=func[1], cargo=func[2])

            return None

        except Exception as e:
            print(f"Erro ao buscar usuário: {e}")
            return None
        finally:
            cursor.close()
            conexao.close()

    def buscar_por_email(self, email):
        """
        Busca um usuário no banco de dados pelo seu email e reconstrói o objeto
        completo (Aluno, Admin ou Funcionario).
        """
        conexao = conectar_banco()
        if not conexao:
            return None
        
        cursor = conexao.cursor()
        try:
            cursor.execute("SELECT * FROM usuario WHERE email = %s", (email,))
            u = cursor.fetchone()
            
            if not u:
                return None

            # Desempacota a tupla 'u' em variáveis com nomes claros
            cpf_usuario, nome_usuario, email_usuario, senha_usuario, data_nasc_usuario, status_usuario = u

            # Tenta encontrar o tipo de usuário
            cursor.execute("SELECT * FROM aluno WHERE cpf = %s", (cpf_usuario,))
            aluno_data = cursor.fetchone()
            if aluno_data:
                # Chama o construtor passando cada argumento pelo seu nome (keyword arguments)
                return Aluno(
                    cpf=cpf_usuario,
                    nome=nome_usuario,
                    email=email_usuario,
                    senha=senha_usuario,
                    data_nasc=data_nasc_usuario,
                    status=status_usuario,
                    matricula=aluno_data[1],
                    curso=aluno_data[2],
                    ano_inicio=aluno_data[3],
                    # Adicione os outros campos de aluno aqui se precisar deles no objeto
                    categoria=aluno_data[4],
                    valor_remuneracao=aluno_data[5],
                    carga_horaria=aluno_data[6],
                    horario_inicio=aluno_data[7],
                    horario_fim=aluno_data[8],
                    id_supervisor_servidor=aluno_data[9]
                )

            # A mesma lógica de correção se aplica para Admin e Funcionario
            cursor.execute("SELECT id_servidor, data_admissao FROM servidor WHERE cpf = %s", (cpf_usuario,))
            serv_data = cursor.fetchone()
            if not serv_data:
                return None
            
            id_servidor, data_admissao = serv_data

            cursor.execute("SELECT * FROM admin WHERE cpf = %s", (cpf_usuario,))
            admin_data = cursor.fetchone()
            if admin_data:
                return Admin(
                    cpf=cpf_usuario, nome=nome_usuario, email=email_usuario, senha=senha_usuario,
                    data_nasc=data_nasc_usuario, status=status_usuario,
                    id_servidor=id_servidor, data_admissao=data_admissao,
                    nivel_acesso=admin_data[1], area_responsabilidade=admin_data[2],
                    data_ultimo_login=admin_data[3]
                )

            cursor.execute("SELECT * FROM funcionario WHERE cpf = %s", (cpf_usuario,))
            func_data = cursor.fetchone()
            if func_data:
                return Funcionario(
                    cpf=cpf_usuario, nome=nome_usuario, email=email_usuario, senha=senha_usuario,
                    data_nasc=data_nasc_usuario, status=status_usuario,
                    id_servidor=id_servidor, data_admissao=data_admissao,
                    departamento=func_data[1], cargo=func_data[2]
                )

            return None

        except Exception as e:
            print(f"Erro ao buscar usuário por email: {e}")
            return None
        finally:
            cursor.close()
            conexao.close()
            
    def buscar_todos_os_usuarios(self):
        """
        Busca todos os usuários do sistema e determina o tipo de cada um.
        Retorna uma lista de dicionários, onde cada dicionário representa um usuário.
        """
        conexao = conectar_banco()
        if not conexao:
            print("Erro: Não foi possível conectar ao banco de dados.")
            return []
        
        # Usamos um cursor que retorna dicionários para facilitar o acesso no template
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        usuarios = []
        try:
            # Esta query usa LEFT JOIN para conectar as tabelas e CASE para definir o tipo
            query = """
                SELECT 
                    u.cpf, 
                    u.nome, 
                    u.email, 
                    u.status,
                    CASE
                        WHEN a.cpf IS NOT NULL THEN 'Admin'
                        WHEN f.cpf IS NOT NULL THEN 'Funcionário'
                        WHEN al.cpf IS NOT NULL THEN 'Aluno'
                        WHEN s.cpf IS NOT NULL THEN 'Servidor'
                        ELSE 'Usuário'
                    END as tipo
                FROM 
                    usuario u
                LEFT JOIN 
                    aluno al ON u.cpf = al.cpf
                LEFT JOIN 
                    servidor s ON u.cpf = s.cpf
                LEFT JOIN 
                    admin a ON u.cpf = a.cpf
                LEFT JOIN 
                    funcionario f ON u.cpf = f.cpf
                ORDER BY 
                    u.nome;
            """
            cursor.execute(query)
            # fetchall() com DictCursor retorna uma lista de objetos semelhantes a dicionários
            resultados = cursor.fetchall()

            # Convertemos os resultados para dicionários padrão do Python
            for linha in resultados:
                usuarios.append(dict(linha))
            
            print(f"DEBUG[DAO]: {len(usuarios)} usuários encontrados no banco de dados.")

        except Exception as e:
            print(f"Erro ao buscar todos os usuários: {e}")
        finally:
            cursor.close()
            conexao.close()
            
        return usuarios
        
    def atualizar_status_usuario(self, cpf, novo_status):
        """
        Atualiza o status de um usuário ('ativo' ou 'inativo') no banco de dados.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        # Validação simples para garantir que o status é válido
        if novo_status not in ['ativo', 'inativo']:
            print(f"Erro: Status '{novo_status}' é inválido.")
            return False

        conexao = conectar_banco()
        if not conexao:
            return False
        
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = "UPDATE usuario SET status = %s WHERE cpf = %s"
            cursor.execute(query, (novo_status, cpf))
            conexao.commit()
            
            # rowcount retorna o número de linhas afetadas. Se for > 0, a atualização funcionou.
            if cursor.rowcount > 0:
                print(f"DEBUG[DAO]: Status do usuário CPF {cpf} atualizado para '{novo_status}'.")
                sucesso = True
            else:
                print(f"DEBUG[DAO]: Nenhum usuário encontrado com o CPF {cpf}. Nenhuma atualização foi feita.")

        except Exception as e:
            conexao.rollback()
            print(f"Erro ao atualizar status do usuário: {e}")
        finally:
            cursor.close()
            conexao.close()
            
        return sucesso
    
    def excluir_usuario(self, cpf):
        """
        Exclui um usuário e seus registros dependentes (aluno, servidor, etc.).
        Retorna True em caso de sucesso, False em caso de falha.
        """
        conexao = conectar_banco()
        if not conexao:
            return False
        
        cursor = conexao.cursor()
        sucesso = False
        try:
            # ON DELETE CASCADE na tabela 'usuario' cuidará de apagar os registros
            # em 'aluno', 'servidor', 'admin', 'funcionario'.
            query = "DELETE FROM usuario WHERE cpf = %s"
            cursor.execute(query, (cpf,))
            conexao.commit()
            if cursor.rowcount > 0:
                sucesso = True
                print(f"DEBUG[DAO]: Usuário CPF {cpf} excluído com sucesso.")
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao excluir usuário: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso
    
    def buscar_todos_os_servidores(self):
        """
        Busca todos os usuários que são servidores e retorna seus nomes e IDs.
        Ideal para preencher um dropdown de supervisores.
        """
        conexao = conectar_banco()
        if not conexao:
            return []
        
        # Usamos DictCursor para facilitar o acesso por nome da coluna
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        servidores = []
        try:
            # Query que junta 'usuario' e 'servidor' para pegar o nome e o ID
            query = """
                SELECT u.nome, s.id_servidor 
                FROM usuario u
                JOIN servidor s ON u.cpf = s.cpf
                ORDER BY u.nome;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            for linha in resultados:
                servidores.append(dict(linha))
            
            print(f"DEBUG[DAO]: Encontrados {len(servidores)} servidores para supervisão.")
        except Exception as e:
            print(f"Erro ao buscar servidores: {e}")
        finally:
            cursor.close()
            conexao.close()
            
        return servidores
from camada_dados.mongo_config import conectar_mongo
from modelos.usuario import Aluno, Funcionario, Admin, Servidor
from datetime import datetime
import psycopg2.extras

class AlunoDao:
    def salvar(self, aluno: Aluno):
        return UsuarioDAO().salvar(aluno) 


class UsuarioDAO:
    
    # --- METODOS ALTERADOS PARA MONGODB ---
    
    def buscar_por_email(self, email):
        """
        [MongoDB] Busca um usuário na coleção 'usuarios' pelo seu email
        e reconstrói o objeto de modelo Python correspondente.
        """
        db = conectar_mongo()
        if db is None:
            return None
        
        try:
            usuario_dict = db.usuarios.find_one({"email": email})

            if not usuario_dict:
                print(f"DEBUG[DAO-Mongo]: Nenhum usuário encontrado com o email: {email}")
                return None

            print(f"DEBUG[DAO-Mongo]: Usuário encontrado: {usuario_dict['nome']} (Tipo: {usuario_dict['tipo']})")
            
            tipo = usuario_dict.get('tipo')
            
            args_comuns = {
                'cpf': usuario_dict['_id'],
                'nome': usuario_dict['nome'],
                'email': usuario_dict['email'],
                'senha': usuario_dict['senha'],
                'data_nasc': usuario_dict.get('data_nasc'),
                'status': usuario_dict.get('status', 'ativo')
            }

            if tipo == 'aluno':
                detalhes = usuario_dict.get('detalhes_aluno', {})
                return Aluno(
                    **args_comuns,
                    matricula=detalhes.get('matricula'),
                    curso=detalhes.get('curso'),
                    ano_inicio=detalhes.get('ano_inicio'),
                    categoria=detalhes.get('categoria'),
                    valor_remuneracao=detalhes.get('valor_remuneracao'),
                    carga_horaria=detalhes.get('carga_horaria'),
                    horario_inicio=detalhes.get('horario_inicio'),
                    horario_fim=detalhes.get('horario_fim'),
                    id_supervisor_servidor=detalhes.get('id_supervisor_servidor')
                )
            
            elif tipo in ['admin', 'funcionario', 'servidor']:
                detalhes_servidor = usuario_dict.get('detalhes_servidor', {})
                args_servidor = {
                    **args_comuns,
                    'id_servidor': detalhes_servidor.get('id_servidor'),
                    'data_admissao': detalhes_servidor.get('data_admissao')
                }
                
                if tipo == 'admin':
                    detalhes_admin = usuario_dict.get('detalhes_admin', {})
                    return Admin(
                        **args_servidor,
                        nivel_acesso=detalhes_admin.get('nivel_acesso'),
                        area_responsabilidade=detalhes_admin.get('area_responsabilidade')
                    )
                
                elif tipo == 'funcionario':
                    detalhes_func = usuario_dict.get('detalhes_funcionario', {})
                    return Funcionario(
                        **args_servidor,
                        departamento=detalhes_func.get('departamento'),
                        cargo=detalhes_func.get('cargo')
                    )
                
                else: # Se o tipo for 'servidor'
                    return Servidor(**args_servidor)
            
            return None

        except Exception as e:
            print(f"Erro ao buscar usuário por email no MongoDB: {e}")
            return None
        
    def salvar(self, usuario):
        """
        [MongoDB] Salva um novo objeto de usuário (qualquer tipo) na coleção 'usuarios'.
        """
        db = conectar_mongo()
        if db is None:
            return False
            
        try:
            # ETAPA 1: Construir o dicionário base para o documento Mongo
            usuario_dict = {
                "_id": usuario.cpf, # Usa o CPF como chave primária (_id)
                "nome": usuario.nome,
                "email": usuario.email,
                "senha": usuario.senha,
                # Garante que o objeto 'date' seja convertido para 'datetime' para o Mongo
                "data_nasc": datetime.combine(usuario.data_nasc, datetime.min.time()) if hasattr(usuario.data_nasc, 'day') else usuario.data_nasc,
                "status": usuario.status,
                "tipo": usuario.tipo
            }
            
            # ETAPA 2: Adicionar os sub-documentos com os detalhes de cada tipo
            if usuario.tipo == 'aluno':
                usuario_dict['detalhes_aluno'] = {
                    "matricula": getattr(usuario, 'matricula', None),
                    "curso": getattr(usuario, 'curso', None),
                    "ano_inicio": getattr(usuario, 'ano_inicio', None),
                    "categoria": getattr(usuario, 'categoria', 'nao_bolsista'),
                    "valor_remuneracao": getattr(usuario, 'valor_remuneracao', None),
                    "carga_horaria": getattr(usuario, 'carga_horaria', None),
                    "horario_inicio": getattr(usuario, 'horario_inicio', None),
                    "horario_fim": getattr(usuario, 'horario_fim', None),
                    "id_supervisor_servidor": getattr(usuario, 'id_supervisor_servidor', None)
                }
            
            # Se for um tipo de Servidor (Admin ou Funcionário)
            elif hasattr(usuario, 'id_servidor'):
                usuario_dict['detalhes_servidor'] = {
                    "id_servidor": usuario.id_servidor,
                    "data_admissao": datetime.combine(usuario.data_admissao, datetime.min.time()) if hasattr(usuario.data_admissao, 'day') else usuario.data_admissao
                }
                if usuario.tipo == 'admin':
                    usuario_dict['detalhes_admin'] = {
                        "nivel_acesso": getattr(usuario, 'nivel_acesso', 1),
                        "area_responsabilidade": getattr(usuario, 'area_responsabilidade', None)
                    }
                elif usuario.tipo == 'funcionario':
                    usuario_dict['detalhes_funcionario'] = {
                        "departamento": getattr(usuario, 'departamento', None),
                        "cargo": getattr(usuario, 'cargo', None)
                    }

            # ETAPA 3: Inserir o documento final no MongoDB
            # Comando Mongo: db.<nome_colecao>.insert_one(documento)
            db.usuarios.insert_one(usuario_dict)
            
            print(f"DEBUG[DAO-Mongo]: Usuário '{usuario.nome}' salvo com sucesso na coleção 'usuarios'.")
            return True
            
        except Exception as e:
            # pymongo.errors.DuplicateKeyError é comum aqui se o CPF (_id) já existir
            print(f"Erro ao salvar usuário no MongoDB: {e}")
            return False
    
    def buscar_todos_os_usuarios(self):
        """
        [MongoDB] Busca todos os documentos da coleção 'usuarios'.
        Retorna uma lista de dicionários.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        usuarios = []
        try:
            # Comando Mongo: db.<colecao>.find({}) busca todos os documentos
            # O segundo argumento ({...}) é a "projeção", define quais campos retornar.
            # 1 = incluir, 0 = excluir.
            cursor = db.usuarios.find(
                {}, 
                {"_id": 1, "nome": 1, "email": 1, "status": 1, "tipo": 1}
            )

            for usuario_dict in cursor:
                # O _id no Mongo é o CPF, renomeamos para consistência com o template
                usuario_dict['cpf'] = usuario_dict.pop('_id')
                usuarios.append(usuario_dict)
            
            print(f"DEBUG[DAO-Mongo]: {len(usuarios)} usuários encontrados na coleção.")
            
        except Exception as e:
            print(f"Erro ao buscar todos os usuários no MongoDB: {e}")
            
        return usuarios
    
    def atualizar_status_usuario(self, cpf, novo_status):
        """
        [MongoDB] Atualiza o status de um usuário na coleção 'usuarios'.
        """
        if novo_status not in ['ativo', 'inativo']:
            return False

        db = conectar_mongo()
        if db is None:
            return False
        
        sucesso = False
        try:
            # Comando Mongo: db.<colecao>.update_one({filtro}, {operador_de_update})
            resultado = db.usuarios.update_one(
                {"_id": cpf}, # Filtro: encontrar o documento onde _id (CPF) é igual ao fornecido
                {"$set": {"status": novo_status}} # Operador de Update: definir ($set) o campo 'status' para o novo valor
            )
            
            # .modified_count > 0 significa que a atualização encontrou e modificou um documento
            if resultado.modified_count > 0:
                print(f"DEBUG[DAO-Mongo]: Status do usuário CPF {cpf} atualizado para '{novo_status}'.")
                sucesso = True
            else:
                print(f"DEBUG[DAO-Mongo]: Nenhum usuário encontrado com o CPF {cpf} para atualizar.")

        except Exception as e:
            print(f"Erro ao atualizar status do usuário no MongoDB: {e}")
            
        return sucesso
    
    def excluir_usuario(self, cpf):
        """
        [MongoDB] Exclui um usuário da coleção 'usuarios'.
        """
        db = conectar_mongo()
        if db is None:
            return False
        
        sucesso = False
        try:
            # Comando Mongo: db.<colecao>.delete_one({filtro})
            resultado = db.usuarios.delete_one({"_id": cpf})
            
            # .deleted_count > 0 significa que um documento foi encontrado e excluído
            if resultado.deleted_count > 0:
                print(f"DEBUG[DAO-Mongo]: Usuário CPF {cpf} excluído com sucesso.")
                sucesso = True
            else:
                print(f"DEBUG[DAO-Mongo]: Nenhum usuário encontrado com o CPF {cpf} para excluir.")

        except Exception as e:
            print(f"Erro ao excluir usuário no MongoDB: {e}")
            
        return sucesso
    
    def buscar_por_cpf(self, cpf):
        """
        [MongoDB] Busca um usuário na coleção 'usuarios' pelo seu CPF (_id).
        """
        db = conectar_mongo()
        if db is None:
            return None
        
        try:
            # A busca é feita pelo campo '_id', que definimos como sendo o CPF.
            usuario_dict = db.usuarios.find_one({"_id": cpf})

            if not usuario_dict:
                print(f"DEBUG[DAO-Mongo]: Nenhum usuário encontrado com o CPF: {cpf}")
                return None

            print(f"DEBUG[DAO-Mongo]: Usuário encontrado: {usuario_dict['nome']} (CPF: {cpf})")
            
            # A lógica para reconstruir o objeto é a mesma do buscar_por_email
            # Para evitar duplicação, podemos criar um método auxiliar.
            # Por enquanto, vamos repetir a lógica para clareza.
            tipo = usuario_dict.get('tipo')
            
            args_comuns = {
                'cpf': usuario_dict['_id'], 'nome': usuario_dict['nome'], 'email': usuario_dict['email'],
                'senha': usuario_dict['senha'], 'data_nasc': usuario_dict.get('data_nasc'),
                'status': usuario_dict.get('status', 'ativo')
            }

            if tipo == 'aluno':
                detalhes = usuario_dict.get('detalhes_aluno', {})
                return Aluno(**args_comuns, matricula=detalhes.get('matricula'), curso=detalhes.get('curso'), ano_inicio=detalhes.get('ano_inicio'))
            
            elif tipo in ['admin', 'funcionario', 'servidor']:
                detalhes_servidor = usuario_dict.get('detalhes_servidor', {})
                args_servidor = {**args_comuns, 'id_servidor': detalhes_servidor.get('id_servidor'), 'data_admissao': detalhes_servidor.get('data_admissao')}
                
                if tipo == 'admin':
                    detalhes_admin = usuario_dict.get('detalhes_admin', {})
                    return Admin(**args_servidor, nivel_acesso=detalhes_admin.get('nivel_acesso'), area_responsabilidade=detalhes_admin.get('area_responsabilidade'))
                
                elif tipo == 'funcionario':
                    detalhes_func = usuario_dict.get('detalhes_funcionario', {})
                    return Funcionario(**args_servidor, departamento=detalhes_func.get('departamento'), cargo=detalhes_func.get('cargo'))
                
                else: # Servidor
                    return Servidor(**args_servidor)
            
            return None

        except Exception as e:
            print(f"Erro ao buscar usuário por CPF no MongoDB: {e}")
            return None
        
    def buscar_todos_os_servidores(self):
        """
        [MongoDB] Busca todos os usuários que são servidores e retorna 
        seus nomes e IDs de servidor.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        servidores = []
        try:
            # Filtro para encontrar documentos onde o campo 'tipo' seja 'servidor', 'admin' ou 'funcionario'.
            filtro = {"tipo": {"$in": ["servidor", "admin", "funcionario"]}}
            
            # Projeção para retornar apenas os campos que nos interessam.
            projecao = {"nome": 1, "detalhes_servidor.id_servidor": 1, "_id": 0}

            cursor = db.usuarios.find(filtro, projecao)

            for doc in cursor:
                # O resultado será algo como: {'nome': 'Admin Geral', 'detalhes_servidor': {'id_servidor': 'SERV001'}}
                servidores.append({
                    "nome": doc.get('nome'),
                    "id_servidor": doc.get('detalhes_servidor', {}).get('id_servidor')
                })
            
            print(f"DEBUG[DAO-Mongo]: Encontrados {len(servidores)} servidores para supervisão.")
            
        except Exception as e:
            print(f"Erro ao buscar servidores no MongoDB: {e}")
            
        return servidores
    
    
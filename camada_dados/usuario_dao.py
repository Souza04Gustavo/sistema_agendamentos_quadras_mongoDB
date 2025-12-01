from camada_dados.mongo_config import conectar_mongo
from pymongo import MongoClient
from modelos.usuario import Aluno, Funcionario, Admin, Servidor
from datetime import datetime

class AlunoDao:
    def salvar(self, aluno: Aluno):
        return UsuarioDAO().salvar(aluno) 

class UsuarioDAO:
    
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
            
            # Helper para reconstruir o objeto
            return self._criar_objeto_usuario_do_dict(usuario_dict)

        except Exception as e:
            print(f"Erro ao buscar usuário por email no MongoDB: {e}")
            return None

    def buscar_por_cpf(self, cpf):
        """
        [MongoDB] Busca um usuário na coleção 'usuarios' pelo seu CPF (_id).
        """
        db = conectar_mongo()
        if db is None:
            return None
        
        try:
            usuario_dict = db.usuarios.find_one({"_id": cpf})

            if not usuario_dict:
                print(f"DEBUG[DAO-Mongo]: Nenhum usuário encontrado com o CPF: {cpf}")
                return None

            # Helper para reconstruir o objeto (evita duplicar código)
            return self._criar_objeto_usuario_do_dict(usuario_dict)

        except Exception as e:
            print(f"Erro ao buscar usuário por CPF no MongoDB: {e}")
            return None

    def _criar_objeto_usuario_do_dict(self, usuario_dict):
        """
        Método auxiliar para converter o dicionário do Mongo de volta para Objeto Python.
        """
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
            
            # CORREÇÃO CRÍTICA: Definir a flag is_bolsista baseada na categoria do banco
            eh_bolsista = (detalhes.get('categoria') == 'bolsista')
            
            return Aluno(
                **args_comuns,
                matricula=detalhes.get('matricula'),
                curso=detalhes.get('curso'),
                ano_inicio=detalhes.get('ano_inicio'),
                is_bolsista=eh_bolsista, # Passa a flag explicitamente
                # Os kwargs abaixo serão capturados pelo **kwargs do Aluno se is_bolsista=True
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
            
            else: # Se o tipo for apenas 'servidor' genérico
                return Servidor(**args_servidor)
        
        return None

    def salvar(self, usuario):
        """
        [MongoDB] Salva um novo objeto de usuário (qualquer tipo) na coleção 'usuarios'.
        """
        db = conectar_mongo()
        if db is None:
            return False
            
        try:
            usuario_dict = {}

            # 1. Tenta usar o método do Modelo (Recomendado se você aplicou a correção anterior)
            if hasattr(usuario, 'get_document_mongo'):
                usuario_dict = usuario.get_document_mongo()
            
            # 2. Fallback: Constrói manualmente se o modelo não tiver o método
            else:
                usuario_dict = {
                    "_id": usuario.cpf,
                    "nome": usuario.nome,
                    "email": usuario.email,
                    "senha": usuario.senha,
                    # Converte date para datetime para o Mongo aceitar sem reclamar
                    "data_nasc": datetime.combine(usuario.data_nasc, datetime.min.time()) if hasattr(usuario.data_nasc, 'day') else usuario.data_nasc,
                    "status": usuario.status,
                    "tipo": usuario.tipo
                }
                
                if usuario.tipo == 'aluno':
                    usuario_dict['detalhes_aluno'] = {
                        "matricula": getattr(usuario, 'matricula', None),
                        "curso": getattr(usuario, 'curso', None),
                        "ano_inicio": getattr(usuario, 'ano_inicio', None),
                        "categoria": getattr(usuario, 'categoria', 'nao_bolsista')
                    }
                    # Se for bolsista, adiciona campos extras no mesmo sub-documento
                    if getattr(usuario, 'is_bolsista', False) or getattr(usuario, 'categoria', '') == 'bolsista':
                        usuario_dict['detalhes_aluno'].update({
                            "valor_remuneracao": getattr(usuario, 'valor_remuneracao', None),
                            "carga_horaria": getattr(usuario, 'carga_horaria', None),
                            "horario_inicio": getattr(usuario, 'horario_inicio', None),
                            "horario_fim": getattr(usuario, 'horario_fim', None),
                            "id_supervisor_servidor": getattr(usuario, 'id_supervisor_servidor', None)
                        })

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

            # Insere no banco
            db.usuarios.insert_one(usuario_dict)
            print(f"DEBUG[DAO-Mongo]: Usuário '{usuario.nome}' salvo com sucesso.")
            return True
            
        except Exception as e:
            print(f"Erro ao salvar usuário no MongoDB: {e}")
            return False
    
    def buscar_todos_os_usuarios(self):
        """
        [MongoDB] Busca todos os documentos da coleção 'usuarios'.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        usuarios = []
        try:
            cursor = db.usuarios.find(
                {}, 
                {"_id": 1, "nome": 1, "email": 1, "status": 1, "tipo": 1}
            )

            for usuario_dict in cursor:
                usuario_dict['cpf'] = usuario_dict.pop('_id')
                usuarios.append(usuario_dict)
            
        except Exception as e:
            print(f"Erro ao buscar todos os usuários: {e}")
            
        return usuarios
    
    def buscar_todos_os_servidores(self):
        """
        [MongoDB] Busca usuários que são servidores para o dropdown de supervisores.
        CORREÇÃO: Busca na coleção 'usuarios', não existe coleção 'servidor'.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        servidores = []
        try:
            # Filtra onde o tipo é um dos cargos de servidor
            filtro = {"tipo": {"$in": ["admin", "funcionario", "servidor"]}}
            projecao = {"_id": 1, "nome": 1, "detalhes_servidor.id_servidor": 1}
            
            cursor = db.usuarios.find(filtro, projecao).sort("nome", 1)

            for doc in cursor:
                # Extrai o id_servidor do sub-documento com segurança
                id_serv = doc.get('detalhes_servidor', {}).get('id_servidor')
                
                servidor_dict = {
                    "cpf": doc["_id"],
                    "nome": doc["nome"],
                    "id_servidor": id_serv
                }
                servidores.append(servidor_dict)

            print(f"DEBUG[DAO-Mongo]: Encontrados {len(servidores)} servidores.")

        except Exception as e:
            print(f"Erro ao buscar servidores no MongoDB: {e}")

        return servidores

    def atualizar_status_usuario(self, cpf, novo_status):
        if novo_status not in ['ativo', 'inativo']:
            return False

        db = conectar_mongo()
        if db is None: return False
        
        try:
            resultado = db.usuarios.update_one(
                {"_id": cpf},
                {"$set": {"status": novo_status}}
            )
            return resultado.modified_count > 0
        except Exception as e:
            print(f"Erro ao atualizar status: {e}")
            return False
    
    def excluir_usuario(self, cpf):
        db = conectar_mongo()
        if db is None: return False
        
        try:
            resultado = db.usuarios.delete_one({"_id": cpf})
            return resultado.deleted_count > 0
        except Exception as e:
            print(f"Erro ao excluir usuário: {e}")
            return False
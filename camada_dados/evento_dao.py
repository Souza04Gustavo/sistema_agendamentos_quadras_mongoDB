# camada_dados/evento_dao.py

from .mongo_config import conectar_mongo
from bson import ObjectId
from datetime import datetime

class EventoDAO:
        
    # --- Metodos do MongoDB ---
    def buscar_todos(self):
        """
        [MongoDB] Busca todos os documentos da coleção 'eventos'.
        Cria campos de compatibilidade para o template.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        eventos = []
        try:
            resultados = db.eventos.find({}).sort([("data_hora_inicio", -1), ("data_fim_recorrencia", -1)])
            eventos_brutos = list(resultados)
            
            # --- Lógica de Compatibilidade CORRIGIDA ---
            for evento in eventos_brutos:
                tipo = evento.get('tipo')
                
                # Cria a chave 'tipo_evento' que o template espera
                if tipo == 'extraordinario':
                    evento['tipo_evento'] = 'Extraordinário'
                    evento['data_principal'] = evento.get('data_hora_inicio')
                    evento['detalhe_tempo'] = evento.get('data_hora_fim')
                elif tipo == 'recorrente':
                    evento['tipo_evento'] = 'Recorrente'
                    evento['data_principal'] = evento.get('data_fim_recorrencia')
                    evento['detalhe_tempo'] = evento.get('regra_recorrencia')
                else:
                    evento['tipo_evento'] = 'Desconhecido'
                    evento['data_principal'] = None
                    evento['detalhe_tempo'] = None
                
                # Simula o nome do admin
                evento['nome_admin'] = evento.get('admin_info', {}).get('nome', 'N/A')
                
                eventos.append(evento)

            print(f"DEBUG[DAO-Mongo]: {len(eventos)} eventos encontrados e processados.")

        except Exception as e:
            print(f"Erro ao buscar todos os eventos no MongoDB: {e}")
            
        return eventos
    
    def excluir(self, id_evento):
        """
        [MongoDB] Exclui um evento da coleção 'eventos' pelo seu _id.
        """
        db = conectar_mongo()
        if db is None:
            return False
            
        sucesso = False
        try:
            # Converte a string do ID para um objeto ObjectId
            obj_id = ObjectId(id_evento)
            
            resultado = db.eventos.delete_one({"_id": obj_id})
            
            if resultado.deleted_count > 0:
                sucesso = True
                print(f"DEBUG[DAO-Mongo]: Evento ID {id_evento} excluído.")
            else:
                print(f"DEBUG[DAO-Mongo]: Nenhum evento com ID {id_evento} encontrado para excluir.")

        except Exception as e:
            print(f"Erro ao excluir evento no MongoDB: {e}")
            
        return sucesso

    def criar(self, cpf_admin_organizador, nome_evento, desc_evento, tipo_evento, dados_tempo, lista_quadras_ids):
        """
        [MongoDB] Cria um novo documento de evento (Extraordinário ou Recorrente).
        Retorna True em caso de sucesso, False em caso de falha.
        """
        db = conectar_mongo()
        if db is None:
            return False
            
        try:
            # --- Etapa 1: Buscar informações embutidas ---
            # Busca o nome do admin para embutir no documento
            admin = db.usuarios.find_one({"_id": cpf_admin_organizador}, {"nome": 1})
            nome_admin = admin.get('nome') if admin else 'Desconhecido'

            # --- Etapa 2: Montar o documento base do evento ---
            documento_evento = {
                # _id será gerado automaticamente pelo MongoDB
                "nome": nome_evento,
                "descricao": desc_evento,
                "cpf_admin_organizador": cpf_admin_organizador,
                "admin_info": {
                    "nome": nome_admin
                },
                "tipo": tipo_evento,
                "quadras_bloqueadas": [
                    {"id_ginasio": id_gin, "num_quadra": num_q} for id_gin, num_q in lista_quadras_ids
                ]
            }

            # --- Etapa 3: Adicionar os campos de tempo específicos ---
            if tipo_evento == 'extraordinario':
                documento_evento['data_hora_inicio'] = datetime.fromisoformat(dados_tempo.get('inicio'))
                documento_evento['data_hora_fim'] = datetime.fromisoformat(dados_tempo.get('fim'))
            
            elif tipo_evento == 'recorrente':
                documento_evento['regra_recorrencia'] = dados_tempo.get('regra')
                documento_evento['data_fim_recorrencia'] = datetime.combine(datetime.fromisoformat(dados_tempo.get('data_fim')), datetime.min.time())

            # --- Etapa 4: Inserir o documento final ---
            resultado = db.eventos.insert_one(documento_evento)
            
            if resultado.inserted_id:
                print(f"DEBUG[DAO-Mongo]: Evento '{nome_evento}' criado com ID {resultado.inserted_id}.")
                return True
            else:
                return False

        except Exception as e:
            print(f"Erro ao criar evento no MongoDB: {e}")
            return False
        
    def quadra_pertence_a_evento(self, id_evento, id_ginasio, num_quadra):
        """
        [MongoDB] Verifica se uma quadra específica está no array 'quadras_bloqueadas' de um evento.
        """
        db = conectar_mongo()
        if db is None:
            return False
            
        try:
            obj_id_evento = ObjectId(id_evento)
            
            # Filtro para encontrar o evento E se a quadra está no array
            filtro = {
                "_id": obj_id_evento,
                "quadras_bloqueadas": {
                    "$elemMatch": {"id_ginasio": int(id_ginasio), "num_quadra": int(num_quadra)}
                }
            }
            
            # find_one retorna o documento se encontrar, ou None se não encontrar
            encontrou = db.eventos.find_one(filtro)
            
            return encontrou is not None
            
        except Exception as e:
            print(f"Erro ao verificar se quadra pertence a evento (MongoDB): {e}")
            return False

    def buscar_recorrentes_por_quadra(self, id_ginasio, num_quadra):
        """
        [MongoDB] Busca todos os eventos recorrentes associados a uma quadra específica.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        recorrentes = []
        try:
            # Filtro para encontrar eventos do tipo 'recorrente' E que contenham
            # a quadra específica no seu array 'quadras_bloqueadas'.
            filtro = {
                "tipo": "recorrente",
                "quadras_bloqueadas": {
                    "$elemMatch": {"id_ginasio": int(id_ginasio), "num_quadra": int(num_quadra)}
                }
            }
            
            resultados = db.eventos.find(filtro)
            recorrentes = list(resultados)

        except Exception as e:
            print(f"Erro ao buscar eventos recorrentes por quadra (MongoDB): {e}")
            
        return recorrentes
    
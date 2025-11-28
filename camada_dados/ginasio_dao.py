# camada_dados/ginasio_dao.py

import psycopg2.extras
from .mongo_config import conectar_mongo

class GinasioDAO:
    # --- Metodos migrados para o MongoDB ---
    
    def buscar_todos(self):
        """
        [MongoDB] Busca todos os ginásios na coleção 'ginasios'.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        ginasios = []
        try:
            # Busca todos os documentos na coleção e ordena por nome
            resultados = db.ginasios.find({}).sort("nome", 1)
            ginasios = list(resultados)
        except Exception as e:
            print(f"Erro ao buscar todos os ginásios no MongoDB: {e}")
            
        return ginasios
    
    def buscar_por_id(self, id_ginasio):
        """[MongoDB] Busca um único ginásio pelo seu _id."""
        db = conectar_mongo()
        if db is None: return None
        try:
            return db.ginasios.find_one({"_id": int(id_ginasio)})
        except Exception as e:
            print(f"Erro ao buscar ginásio por ID no MongoDB: {e}")
            return None

    def criar(self, nome, endereco, capacidade):
        """[MongoDB] Insere um novo ginásio com arrays vazios para quadras e materiais."""
        db = conectar_mongo()
        if db is None: return None
        try:
            # Para garantir um _id numérico e sequencial, simulamos o auto-incremento
            ultimo_ginasio = db.ginasios.find_one(sort=[("_id", -1)])
            novo_id = ultimo_ginasio['_id'] + 1 if ultimo_ginasio else 1
            
            novo_ginasio = {
                "_id": novo_id,
                "nome": nome,
                "endereco": endereco,
                "capacidade": int(capacidade) if capacidade else None,
                "quadras": [], # Array de quadras começa vazio
                "materiais_esportivos": [] # Array de materiais começa vazio
            }
            resultado = db.ginasios.insert_one(novo_ginasio)
            return resultado.inserted_id
        except Exception as e:
            print(f"Erro ao criar ginásio no MongoDB: {e}")
            return None

    def atualizar(self, id_ginasio, nome, endereco, capacidade):
        """[MongoDB] Atualiza os dados de um ginásio."""
        db = conectar_mongo()
        if db is None: return False
        try:
            resultado = db.ginasios.update_one(
                {"_id": int(id_ginasio)},
                {"$set": {
                    "nome": nome,
                    "endereco": endereco,
                    "capacidade": int(capacidade) if capacidade else None
                }}
            )
            return resultado.modified_count > 0
        except Exception as e:
            print(f"Erro ao atualizar ginásio no MongoDB: {e}")
            return False

    def excluir(self, id_ginasio):
        """[MongoDB] Exclui um ginásio da coleção."""
        db = conectar_mongo()
        if db is None: return False
        try:
            resultado = db.ginasios.delete_one({"_id": int(id_ginasio)})
            return resultado.deleted_count > 0
        except Exception as e:
            print(f"Erro ao excluir ginásio no MongoDB: {e}")
            return False

    # --- MÉTODOS RELACIONADOS A QUADRAS (AGORA DENTRO DE GINASIODAO) ---

    def buscar_todas_as_quadras(self):
        """[MongoDB] Busca todas as quadras de todos os ginásios."""
        db = conectar_mongo()
        if db is None: return []
        quadras = []
        try:
            pipeline = [
                {"$unwind": "$quadras"},
                {"$project": {
                    "_id": 0,
                    "id_ginasio": "$_id",
                    "nome_ginasio": "$nome",
                    "num_quadra": "$quadras.num_quadra",
                    "tipo_piso": "$quadras.tipo_piso",
                    "cobertura": "$quadras.cobertura",
                    "status": "$quadras.status"
                }}
            ]
            resultados = db.ginasios.aggregate(pipeline)
            quadras = list(resultados)
        except Exception as e:
            print(f"Erro ao buscar todas as quadras no MongoDB: {e}")
        return quadras

    def criar_quadra(self, id_ginasio, num_quadra, capacidade, tipo_piso, cobertura):
        """[MongoDB] Adiciona uma nova quadra (sub-documento) a um ginásio."""
        db = conectar_mongo()
        if db is None: return False
        try:
            nova_quadra = {
                "num_quadra": int(num_quadra),
                "capacidade": int(capacidade) if capacidade else None,
                "tipo_piso": tipo_piso,
                "cobertura": True if cobertura else False,
                "status": "disponivel",
                "esportes_permitidos": []
            }
            resultado = db.ginasios.update_one(
                {"_id": int(id_ginasio)},
                {"$push": {"quadras": nova_quadra}}
            )
            return resultado.modified_count > 0
        except Exception as e:
            print(f"Erro ao criar quadra no MongoDB: {e}")
            return False

    def atualizar_status_quadra(self, id_ginasio, num_quadra, novo_status):
        """[MongoDB] Atualiza o status de uma quadra específica dentro de um ginásio."""
        db = conectar_mongo()
        if db is None: return False
        try:
            resultado = db.ginasios.update_one(
                {"_id": int(id_ginasio), "quadras.num_quadra": int(num_quadra)},
                {"$set": {"quadras.$.status": novo_status}}
            )
            return resultado.modified_count > 0
        except Exception as e:
            print(f"Erro ao atualizar status da quadra no MongoDB: {e}")
            return False

    def excluir_quadra(self, id_ginasio, num_quadra):
        """[MongoDB] Remove uma quadra (sub-documento) de um ginásio."""
        db = conectar_mongo()
        if db is None: return False
        try:
            resultado = db.ginasios.update_one(
                {"_id": int(id_ginasio)},
                {"$pull": {"quadras": {"num_quadra": int(num_quadra)}}}
            )
            return resultado.modified_count > 0
        except Exception as e:
            print(f"Erro ao excluir quadra no MongoDB: {e}")
            return False

    # --- MÉTODOS DE ASSOCIAÇÃO DE ESPORTES (AGORA DENTRO DE GINASIODAO) ---
    
    def buscar_esportes_da_quadra(self, id_ginasio, num_quadra):
        """[MongoDB] Busca os IDs de esportes associados a uma quadra."""
        db = conectar_mongo()
        if db is None: return []
        try:
            # Busca o ginásio e a quadra específica, e projeta apenas o campo de esportes
            resultado = db.ginasios.find_one(
                {"_id": int(id_ginasio), "quadras.num_quadra": int(num_quadra)},
                {"quadras.esportes_permitidos.$": 1}
            )
            if resultado and 'quadras' in resultado and resultado['quadras']:
                return resultado['quadras'][0].get('esportes_permitidos', [])
        except Exception as e:
            print(f"Erro ao buscar esportes da quadra no MongoDB: {e}")
        return []

    def atualizar_esportes_da_quadra(self, id_ginasio, num_quadra, lista_ids_esportes):
        """[MongoDB] Atualiza a lista de esportes de uma quadra."""
        db = conectar_mongo()
        if db is None: return False
        try:
            # Garante que os IDs são inteiros, se o seu EsporteDAO usa IDs numéricos
            lista_ids_int = [int(id) for id in lista_ids_esportes]

            resultado = db.ginasios.update_one(
                {"_id": int(id_ginasio), "quadras.num_quadra": int(num_quadra)},
                {"$set": {"quadras.$.esportes_permitidos": lista_ids_int}}
            )
            return resultado.modified_count > 0
        except Exception as e:
            print(f"Erro ao atualizar esportes da quadra no MongoDB: {e}")
            return False
        
        

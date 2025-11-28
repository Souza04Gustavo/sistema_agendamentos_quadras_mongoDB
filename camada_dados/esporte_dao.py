# camada_dados/esporte_dao.py
from .mongo_config import conectar_mongo
from bson import ObjectId

class EsporteDAO:
    # --- Mongo DB metodos alterados ---
    def buscar_todos(self):
        """
        [MongoDB] Busca todos os documentos da coleção 'esportes', ordenados por nome.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        esportes = []
        try:
            # db.<colecao>.find({}).sort("campo", 1 para ascendente)
            resultados = db.esportes.find({}).sort("nome", 1)
            # É importante converter o cursor para uma lista
            esportes = list(resultados)
            print(f"DEBUG[DAO-Mongo]: {len(esportes)} esportes encontrados.")
        except Exception as e:
            print(f"Erro ao buscar esportes no MongoDB: {e}")
            
        return esportes

    def buscar_por_id(self, id_esporte):
        """
        [MongoDB] Busca um único esporte pelo seu _id.
        """
        db = conectar_mongo()
        if db is None:
            return None
            
        try:
            # Converte a string do ID para um objeto ObjectId do MongoDB
            obj_id = ObjectId(id_esporte)
            esporte = db.esportes.find_one({"_id": obj_id})
            return esporte
        except Exception as e:
            print(f"Erro ao buscar esporte por ID no MongoDB: {e}")
            return None

    def criar(self, nome, max_jogadores):
        """
        [MongoDB] Insere um novo esporte na coleção 'esportes'.
        Retorna o ID do novo esporte se for bem-sucedido.
        """
        db = conectar_mongo()
        if db is None:
            return None
            
        try:
            novo_esporte = {
                "nome": nome,
                "max_jogadores": int(max_jogadores) if max_jogadores else None
            }
            resultado = db.esportes.insert_one(novo_esporte)
            print(f"DEBUG[DAO-Mongo]: Novo esporte '{nome}' criado com ID {resultado.inserted_id}.")
            return resultado.inserted_id
        except Exception as e:
            print(f"Erro ao criar esporte no MongoDB: {e}")
            return None

    def atualizar(self, id_esporte, nome, max_jogadores):
        """
        [MongoDB] Atualiza os dados de um esporte existente.
        """
        db = conectar_mongo()
        if db is None:
            return False
            
        try:
            obj_id = ObjectId(id_esporte)
            resultado = db.esportes.update_one(
                {"_id": obj_id},
                {"$set": {
                    "nome": nome,
                    "max_jogadores": int(max_jogadores) if max_jogadores else None
                }}
            )
            return resultado.modified_count > 0
        except Exception as e:
            print(f"Erro ao atualizar esporte no MongoDB: {e}")
            return False

    def excluir(self, id_esporte):
        """
        [MongoDB] Exclui um esporte da coleção.
        """
        db = conectar_mongo()
        if db is None:
            return False
            
        try:
            obj_id = ObjectId(id_esporte)
            resultado = db.esportes.delete_one({"_id": obj_id})
            return resultado.deleted_count > 0
        except Exception as e:
            print(f"Erro ao excluir esporte no MongoDB: {e}")
            return False
    
    
# camada_dados/quadra_dao.py

from bson import ObjectId
from .mongo_config import conectar_mongo

class QuadraDAO:
    # --- metodos do MongoDB ---
    def buscar_todas_as_quadras(self):
        """
        [MongoDB] Busca todas as quadras de todos os ginásios, simulando um JOIN.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        quadras = []
        try:
            pipeline = [
                {"$unwind": "$quadras"}, # "Desmonta" o array de quadras
                {"$project": {
                    "_id": 0, # Exclui o _id do ginásio do resultado final
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
            print(f"DEBUG[DAO-Mongo]: {len(quadras)} quadras encontradas via agregação.")
        except Exception as e:
            print(f"Erro ao buscar todas as quadras no MongoDB: {e}")
            
        return quadras

    def criar_quadra(self, id_ginasio, num_quadra, capacidade, tipo_piso, cobertura):
        """
        [MongoDB] Adiciona uma nova quadra (sub-documento) a um ginásio.
        """
        db = conectar_mongo()
        if db is None:
            return False
            
        try:
            nova_quadra = {
                "num_quadra": int(num_quadra),
                "capacidade": int(capacidade) if capacidade else None,
                "tipo_piso": tipo_piso,
                "cobertura": True if cobertura else False,
                "status": "disponivel",
                "esportes_permitidos": [] # Array de esportes começa vazio
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
        """
        [MongoDB] Atualiza o status de uma quadra específica dentro de um ginásio.
        """
        if novo_status not in ['disponivel', 'manutencao', 'interditada']:
            return False
            
        db = conectar_mongo()
        if db is None:
            return False
            
        try:
            resultado = db.ginasios.update_one(
                # Filtro para encontrar o ginásio e a quadra correta dentro do array
                {"_id": int(id_ginasio), "quadras.num_quadra": int(num_quadra)},
                # Usa o positional operator ($) para atualizar apenas o status da quadra encontrada
                {"$set": {"quadras.$.status": novo_status}}
            )
            return resultado.modified_count > 0
        except Exception as e:
            print(f"Erro ao atualizar status da quadra no MongoDB: {e}")
            return False

    def excluir_quadra(self, id_ginasio, num_quadra):
        """
        [MongoDB] Remove uma quadra (sub-documento) do array de um ginásio.
        """
        db = conectar_mongo()
        if db is None:
            return False
            
        try:
            # $pull remove um elemento de um array que corresponde a uma condição
            resultado = db.ginasios.update_one(
                {"_id": int(id_ginasio)},
                {"$pull": {"quadras": {"num_quadra": int(num_quadra)}}}
            )
            return resultado.modified_count > 0
        except Exception as e:
            print(f"Erro ao excluir quadra no MongoDB: {e}")
            return False

    def buscar_esportes_da_quadra(self, id_ginasio, num_quadra):
        """
        [MongoDB] Busca os IDs de esportes associados a uma quadra.
        """
        db = conectar_mongo()
        if db is None:
            return []
            
        try:
            resultado = db.ginasios.find_one(
                {"_id": int(id_ginasio), "quadras.num_quadra": int(num_quadra)},
                # Projeção para retornar apenas o campo de esportes da quadra encontrada
                {"_id": 0, "quadras.esportes_permitidos.$": 1}
            )
            if resultado and 'quadras' in resultado and resultado['quadras']:
                return resultado['quadras'][0].get('esportes_permitidos', [])
        except Exception as e:
            print(f"Erro ao buscar esportes da quadra no MongoDB: {e}")
            
        return []

    def atualizar_esportes_da_quadra(self, id_ginasio, num_quadra, lista_ids_esportes):
        """
        [MongoDB] Atualiza a lista de strings de IDs de esportes de uma quadra.
        """
        db = conectar_mongo()
        if db is None:
            return False
            
        try:
            # --- DEBUG: Ver o que está sendo recebido ---
            print("\n--- DEBUG[DAO]: Atualizando Esportes da Quadra ---")
            print(f"  -> Ginásio ID: {id_ginasio} (tipo: {type(id_ginasio)})")
            print(f"  -> Quadra Nº: {num_quadra} (tipo: {type(num_quadra)})")
            print(f"  -> Lista de IDs de Esportes: {lista_ids_esportes} (tipo do primeiro item: {type(lista_ids_esportes[0]) if lista_ids_esportes else 'N/A'})")

            # Monta o filtro e a operação de atualização
            filtro = {"_id": int(id_ginasio), "quadras.num_quadra": int(num_quadra)}
            operacao_update = {"$set": {"quadras.$.esportes_permitidos": lista_ids_esportes}}
            
            # --- DEBUG: Ver o comando exato que será enviado ao Mongo ---
            print(f"  -> Filtro Mongo: {filtro}")
            print(f"  -> Operação Update Mongo: {operacao_update}")

            resultado = db.ginasios.update_one(filtro, operacao_update)
            
            print(f"  -> Resultado: Matched={resultado.matched_count}, Modified={resultado.modified_count}")
            
            return resultado.matched_count > 0

        except Exception as e:
            print(f"  -> ERRO[DAO] ao atualizar esportes da quadra: {e}")
            return False
        

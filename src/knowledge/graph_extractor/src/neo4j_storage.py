import logging
from typing import Any, Dict, List, Optional, Tuple
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, Record, Query
from neo4j.exceptions import Neo4jError
from .base import BaseGraphStorage
from .prompt import constraint_query  # Importo la query corretta per il constraint

# Configurazione di logging con livello DEBUG di default
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Neo4jGraphStorage(BaseGraphStorage):
    """Implementazione di BaseGraphStorage per Neo4j."""

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """
        Inizializza la connessione a Neo4j.

        Args:
            uri: URI del database Neo4j (es. "neo4j://localhost:7687").
            user: Nome utente per la connessione.
            password: Password per la connessione.
            database: Nome del database a cui connettersi.
        """
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._driver: Optional[AsyncDriver] = None
        logger.info(f"Inizializzazione Neo4jGraphStorage per database: {database} su {uri}")
        logger.debug(f"Parametri di connessione configurati: uri={uri}, user={user}, database={database}")

    async def initialize(self) -> None:
        """Inizializza il driver Neo4j e verifica la connettività."""
        if self._driver:
            logger.debug("Driver esistente trovato, chiusura in corso...")
            await self._driver.close()

        try:
            logger.debug(f"Creazione di un nuovo driver Neo4j per {self._uri}")
            self._driver = AsyncGraphDatabase.driver(self._uri, auth=(self._user, self._password))
            logger.debug("Verifica della connettività in corso...")
            await self._driver.verify_connectivity()
            logger.info("Connessione a Neo4j stabilita e verificata.")
            # Opzionale: Creare indici/constraint per migliorare le prestazioni
            logger.debug("Creazione constraint per migliorare le prestazioni...")
            await self._create_constraints()
        except Neo4jError as e:
            logger.error(f"Errore durante la connessione a Neo4j: {e}")
            self._driver = None
            raise

    async def _create_constraints(self) -> None:
        """Crea constraint sull'ID dei nodi per garantire unicità e migliorare le query."""
        async with self._driver.session(database=self._database) as session:
            try:
                # Utilizzo la sintassi corretta per il constraint importata da prompt.py
                logger.debug(f"Esecuzione query per constraint: {constraint_query}")
                await session.run(constraint_query)
                logger.info("Constraint 'node_id_unique' assicurato.")
            except Neo4jError as e:
                # Potrebbe fallire se label diverse hanno proprietà 'id' non uniche globalmente
                # senza label specificate. In un'implementazione reale, potresti voler
                # creare constraint per label specifiche.
                logger.warning(f"Impossibile creare constraint generico 'node_id_unique': {e}. "
                               "Considera constraint specifici per label.")

    async def close(self) -> None:
        """Chiude la connessione al driver Neo4j."""
        if self._driver:
            logger.info("Chiusura della connessione Neo4j.")
            logger.debug("Chiamata al metodo close() del driver Neo4j")
            await self._driver.close()
            self._driver = None
            logger.debug("Driver Neo4j chiuso con successo.")

    async def _execute_read(self, query: str, params: Dict[str, Any] = None) -> List[Record]:
        """Esegue una query Cypher di lettura."""
        if not self._driver:
            logger.error("Tentativo di eseguire query senza driver inizializzato")
            raise ConnectionError("Driver Neo4j non inizializzato.")
        
        logger.debug(f"Esecuzione query di lettura: {query}, params: {params}")
        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, params)
            # Raccolta dei record usando un loop asincrono invece di result.list()
            records = []
            async for record in result:
                records.append(record)
            logger.debug(f"Query di lettura completata, {len(records)} record restituiti")
            return records

    async def _execute_write(self, query: str, params: Dict[str, Any] = None) -> None:
        """Esegue una query Cypher di scrittura."""
        if not self._driver:
            logger.error("Tentativo di eseguire query senza driver inizializzato")
            raise ConnectionError("Driver Neo4j non inizializzato.")
        
        logger.debug(f"Esecuzione query di scrittura: {query}, params: {params}")
        async with self._driver.session(database=self._database) as session:
            await session.run(query, params) # run() in scrittura non restituisce dati direttamente
            logger.debug("Query di scrittura completata con successo")

    async def has_node(self, node_id: str) -> bool:
        """Verifica se un nodo esiste."""
        logger.debug(f"Verifica esistenza nodo con id: {node_id}")
        query = "MATCH (n {id: $node_id}) RETURN n LIMIT 1"
        result = await self._execute_read(query, {"node_id": node_id})
        exists = len(result) > 0
        logger.debug(f"Nodo {node_id} {'trovato' if exists else 'non trovato'}")
        return exists

    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        """Verifica se un arco specifico esiste (ignora tipo di relazione per ora)."""
        # Nota: Questa query trova *qualsiasi* relazione tra i due nodi.
        # Potrebbe essere necessario raffinare se i tipi di relazione sono importanti.
        logger.debug(f"Verifica esistenza arco da {source_node_id} a {target_node_id}")
        query = """
        MATCH (n1 {id: $source_id})-[r]->(n2 {id: $target_id})
        RETURN r LIMIT 1
        """
        result = await self._execute_read(query, {"source_id": source_node_id, "target_id": target_node_id})
        exists = len(result) > 0
        logger.debug(f"Arco da {source_node_id} a {target_node_id} {'trovato' if exists else 'non trovato'}")
        return exists

    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Recupera un nodo per ID."""
        logger.debug(f"Recupero nodo con id: {node_id}")
        query = "MATCH (n {id: $node_id}) RETURN properties(n) as props"
        result = await self._execute_read(query, {"node_id": node_id})
        if result:
            node_props = dict(result[0]["props"])
            logger.debug(f"Nodo {node_id} trovato con proprietà: {node_props}")
            return node_props
        logger.debug(f"Nodo {node_id} non trovato")
        return None

    async def get_edge(self, source_node_id: str, target_node_id: str) -> Optional[Dict[str, Any]]:
        """Recupera le proprietà di un arco specifico (il primo trovato)."""
        # Nota: Restituisce le proprietà della *prima* relazione trovata.
        logger.debug(f"Recupero proprietà arco da {source_node_id} a {target_node_id}")
        query = """
        MATCH (n1 {id: $source_id})-[r]->(n2 {id: $target_id})
        RETURN properties(r) as props LIMIT 1
        """
        result = await self._execute_read(query, {"source_id": source_node_id, "target_id": target_node_id})
        if result and result[0]["props"] is not None:
            edge_props = dict(result[0]["props"])
            logger.debug(f"Arco trovato con proprietà: {edge_props}")
            return edge_props
        logger.debug(f"Nessun arco trovato da {source_node_id} a {target_node_id}")
        return None # Potrebbe non avere proprietà

    async def get_node_edges(self, source_node_id: str) -> Optional[List[Tuple[str, str]]]:
        """Recupera tutti gli archi *uscenti* da un nodo."""
        logger.debug(f"Recupero archi uscenti dal nodo {source_node_id}")
        query = """
        MATCH (n1 {id: $source_id})-[r]->(n2)
        RETURN n1.id AS source_id, n2.id AS target_id
        """
        result = await self._execute_read(query, {"source_id": source_node_id})
        if result:
            edges = [(record["source_id"], record["target_id"]) for record in result]
            logger.debug(f"Trovati {len(edges)} archi uscenti dal nodo {source_node_id}: {edges}")
            return edges
        logger.debug(f"Nessun arco uscente trovato per il nodo {source_node_id}")
        return [] # Ritorna lista vuota se non ci sono archi uscenti

    async def upsert_node(self, node_id: str, node_data: Dict[str, Any]) -> None:
        """Inserisce o aggiorna un nodo."""
        logger.info(f"Upsert nodo con id: {node_id}")
        logger.debug(f"Dati nodo: {node_data}")
        
        # Assicurati che l'ID sia anche nei dati per MERGE
        node_properties = node_data.copy()
        node_properties['id'] = node_id

        # Determina la label (se presente)
        label = node_properties.pop('label', 'Node') # Usa 'Node' come default se non specificato
        logger.debug(f"Label del nodo: {label}")

        # Query MERGE per creare o aggiornare il nodo
        # Usiamo SET p += $props per aggiornare le proprietà esistenti senza sovrascrivere l'intero nodo
        query = f"""
        MERGE (n:{label} {{id: $node_id}})
        SET n += $props
        """
        await self._execute_write(query, {"node_id": node_id, "props": node_properties})
        logger.info(f"Nodo {node_id} creato/aggiornato con successo")

    async def upsert_edge(self, source_node_id: str, target_node_id: str, edge_data: Dict[str, Any]) -> None:
        """Inserisce o aggiorna un arco."""
        logger.info(f"Upsert arco da {source_node_id} a {target_node_id}")
        logger.debug(f"Dati arco: {edge_data}")
        
        # Determina il tipo di relazione (se presente)
        relation_type = edge_data.pop('relation_type', 'RELATED_TO') # Usa 'RELATED_TO' come default
        logger.debug(f"Tipo di relazione: {relation_type}")

        edge_properties = edge_data.copy()

        # Query MERGE per creare o aggiornare l'arco
        # Trova i nodi sorgente e destinazione, poi crea/aggiorna la relazione
        query = f"""
        MATCH (n1 {{id: $source_id}}), (n2 {{id: $target_id}})
        MERGE (n1)-[r:{relation_type}]->(n2)
        SET r += $props
        """
        await self._execute_write(query, {
            "source_id": source_node_id,
            "target_id": target_node_id,
            "props": edge_properties
        })
        logger.info(f"Arco da {source_node_id} a {target_node_id} creato/aggiornato con successo")

    async def delete_node(self, node_id: str) -> None:
        """Elimina un nodo e tutti i suoi archi."""
        logger.info(f"Eliminazione nodo {node_id} e relativi archi")
        query = "MATCH (n {id: $node_id}) DETACH DELETE n"
        await self._execute_write(query, {"node_id": node_id})
        logger.info(f"Nodo {node_id} eliminato con successo")

    async def remove_nodes(self, nodes: List[str]) -> None:
        """Elimina una lista di nodi."""
        # Esegui l'eliminazione in batch per efficienza, se possibile
        # Neo4j gestisce bene le liste in clausole WHERE id IN [...]
        logger.info(f"Eliminazione di {len(nodes)} nodi: {nodes}")
        query = "MATCH (n) WHERE n.id IN $node_ids DETACH DELETE n"
        await self._execute_write(query, {"node_ids": nodes})
        logger.info(f"{len(nodes)} nodi eliminati con successo")

    async def remove_edges(self, edges: List[Tuple[str, str]]) -> None:
        """Elimina una lista di archi."""
        # È più complesso eliminare archi specifici in batch senza conoscere il tipo.
        # Iteriamo e cancelliamo uno per uno per semplicità.
        # Una soluzione più performante potrebbe richiedere UNWIND in Cypher.
        # Nota: Questa implementazione elimina la *prima* relazione trovata tra source e target.
        logger.info(f"Eliminazione di {len(edges)} archi")
        query = """
        MATCH (n1 {id: $source_id})-[r]->(n2 {id: $target_id})
        DELETE r
        LIMIT 1
        """
        # Per eliminare TUTTE le relazioni tra due nodi, rimuovere LIMIT 1
        # query = """
        # MATCH (n1 {id: $source_id})-[r]->(n2 {id: $target_id})
        # DELETE r
        # """
        for source_id, target_id in edges:
            logger.debug(f"Eliminazione arco da {source_id} a {target_id}")
            await self._execute_write(query, {"source_id": source_id, "target_id": target_id})
        logger.info(f"{len(edges)} archi eliminati con successo")

    async def get_all_labels(self) -> List[str]:
        """Recupera tutte le label dei nodi presenti nel database."""
        logger.debug("Recupero di tutte le label dei nodi presenti nel database")
        query = "CALL db.labels() YIELD label RETURN label"
        result = await self._execute_read(query)
        labels = [record["label"] for record in result]
        logger.debug(f"Label trovate: {labels}")
        return labels

    async def get_knowledge_graph(self, node_label: Optional[str] = None, depth: int = 3, limit: int = 1000) -> Any:
        """
        Recupera un sottografo del knowledge graph.
        Restituisce una lista di percorsi (nodi e relazioni).
        """
        logger.info(f"Recupero knowledge graph con label: {node_label}, profondità: {depth}, limite: {limit}")
        
        if node_label:
             match_clause = f"MATCH p=(n:{node_label})-[*1..{depth}]-(m)"
        else:
             match_clause = f"MATCH p=(n)-[*1..{depth}]-(m)" # Cerca da qualsiasi nodo se label non specificata
        
        logger.debug(f"Clausola MATCH per la query: {match_clause}")

        query = f"""
        {match_clause}
        RETURN p LIMIT {limit}
        """
        # L'esecuzione di questa query potrebbe essere pesante.
        # Restituisce oggetti Path di Neo4j. Potrebbe essere necessario
        # processarli ulteriormente per convertirli in un formato standard (es. nodi e archi separati).
        logger.info(f"Recupero knowledge graph con label '{node_label}', profondità {depth}, limite {limit}")
        async with self._driver.session(database=self._database) as session:
            logger.debug(f"Esecuzione query: {query}")
            result = await session.run(Query(query)) # Usiamo Query per evitare problemi con f-string non parametrizzate
            # Estrarre e formattare i dati dai percorsi Neo4j
            paths_data = []
            async for record in result:
                 path = record["p"]
                 path_info = {
                     "nodes": [dict(node.items()) for node in path.nodes],
                     "relationships": [
                         {
                             "start_node": dict(rel.start_node.items()),
                             "end_node": dict(rel.end_node.items()),
                             "type": rel.type,
                             "properties": dict(rel.items())
                         } for rel in path.relationships]
                 }
                 paths_data.append(path_info)
            
            logger.info(f"Trovati {len(paths_data)} percorsi nel knowledge graph")
            logger.debug(f"Primi {min(3, len(paths_data))} percorsi: {paths_data[:3] if paths_data else []}")
            # Potresti voler restituire i dati in un formato diverso,
            # ad esempio una lista di nodi e una lista di archi uniche.
            return paths_data # Restituisce la lista di percorsi processati

    async def index_done_callback(self) -> bool:
        """Callback dopo che l'indicizzazione è completata (semplice implementazione)."""
        logger.info("Callback index_done chiamato.")
        logger.debug("Esecuzione azioni post-indicizzazione, se presenti")
        # Qui potresti aggiungere logica specifica post-indicizzazione, se necessario.
        return True

    async def drop(self) -> Dict[str, str]:
        """Elimina tutti i dati dal database (NODI E RELAZIONI). ATTENZIONE!"""
        logger.warning(f"Tentativo di eliminare TUTTI i dati dal database: {self._database}")
        try:
            query = "MATCH (n) DETACH DELETE n"
            logger.debug(f"Esecuzione query per eliminare tutti i dati: {query}")
            await self._execute_write(query)
            logger.info(f"Tutti i dati eliminati con successo dal database: {self._database}")
            return {"status": "success", "message": f"Database {self._database} svuotato."}
        except Neo4jError as e:
            logger.error(f"Errore durante l'eliminazione dei dati: {e}")
            return {"status": "error", "message": str(e)}

    async def __aenter__(self):
        """Supporto per context manager async: inizializza la connessione."""
        logger.debug("Chiamata __aenter__ del context manager")
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Supporto per context manager async: chiude la connessione."""
        logger.debug("Chiamata __aexit__ del context manager")
        await self.close()

# Esempio di utilizzo (richiede un'istanza Neo4j in esecuzione)
async def main():
    # Sostituisci con i tuoi dettagli di connessione
    NEO4J_URI = "neo4j://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "your_password" # Cambia la password!
    NEO4J_DATABASE = "neo4j"

    storage = Neo4jGraphStorage(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)

    try:
        async with storage: # Usa il context manager per inizializzare e chiudere
            # Testare le operazioni
            await storage.upsert_node("node1", {"label": "Person", "name": "Alice", "age": 30})
            await storage.upsert_node("node2", {"label": "Person", "name": "Bob", "age": 25})
            await storage.upsert_edge("node1", "node2", {"relation_type": "FRIENDS_WITH", "since": 2020})

            print("Nodo 'node1' esiste:", await storage.has_node("node1"))
            print("Nodo 'node3' esiste:", await storage.has_node("node3"))
            print("Arco 'node1' -> 'node2' esiste:", await storage.has_edge("node1", "node2"))

            node1_data = await storage.get_node("node1")
            print("Dati nodo 'node1':", node1_data)

            edge_data = await storage.get_edge("node1", "node2")
            print("Dati arco 'node1' -> 'node2':", edge_data)

            node1_edges = await storage.get_node_edges("node1")
            print("Archi uscenti da 'node1':", node1_edges)

            all_labels = await storage.get_all_labels()
            print("Tutte le label:", all_labels)

            # Esempio di recupero grafo (potrebbe essere vuoto se i nodi non hanno label Person)
            kg_subset = await storage.get_knowledge_graph(node_label="Person", depth=2)
            print("Sottografo Knowledge Graph (Persone):", kg_subset)

            # Pulizia (opzionale)
            # await storage.remove_nodes(["node1", "node2"])
            # print("Nodi eliminati.")
            # Oppure svuota tutto il DB (attenzione!)
            # await storage.drop()
            # print("Database svuotato.")

    except ConnectionError as e:
        print(f"Errore di connessione: {e}")
    except Exception as e:
        print(f"Errore durante l'esecuzione: {e}")

if __name__ == "__main__":
    import asyncio
    # Esegui l'esempio solo se lo script è chiamato direttamente
    # Commenta o rimuovi la password prima del commit!
    # asyncio.run(main())
    print("Esempio di utilizzo commentato. Rimuovere il commento da 'asyncio.run(main())' e impostare la password per eseguirlo.") 
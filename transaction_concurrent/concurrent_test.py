from neo4j import GraphDatabase
import threading, time

URI = "neo4j://localhost:7687"
USER = "neo4j"
PASSWORD = "neo4jpassword"
DB = "mridata"

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "neo4jpassword"))


def txn_A():
    with driver.session(database=DB) as session:
        tx = session.begin_transaction()
        print("[A] Begin. Creating relationship (9998)-[:REL_A_C]->(9999)")
        tx.run("""
            MATCH (a:Patient {PatientId:9998}), (c:Patient {PatientId:9999})
            CREATE (a)-[:REL_A_C]->(c)
        """)
        print("[A] Holding lock for 8 seconds...")
        time.sleep(8)
        print("[A] Committed.")
        tx.commit()

def txn_B():
    time.sleep(1)  # ensure A runs first
    with driver.session(database=DB) as session:
        tx = session.begin_transaction()
        print("[B] Begin. Trying to delete node 1 (will block)")
        try:
            tx.run("MATCH (a:Patient {PatientId:9999}) DETACH DELETE a")
            print("[B] Committed.")
            tx.commit()
        except Exception as e:
            print("[B] ERROR:", e)

t1 = threading.Thread(target=txn_A)
t2 = threading.Thread(target=txn_B)

t1.start()
t2.start()

t1.join()
t2.join()

driver.close()

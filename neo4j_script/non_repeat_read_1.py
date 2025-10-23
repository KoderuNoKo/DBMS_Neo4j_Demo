import threading, time
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "neo4jpassword")
DB = "neo4j"

driver = GraphDatabase.driver(URI, auth=AUTH)

def session_a_work():
    with driver.session(database=DB) as session:
        tx = session.begin_transaction()
        print("\nSession A: First read (before B commits)")
        res1 = tx.run("""
            MATCH (m:Movie)
            WHERE m.title CONTAINS 'Star'
            RETURN count(m) AS c
        """).single()["c"]
        print("Count 1 =", res1)
        input("Press Enter after Session B commits ... ")
        res2 = tx.run("""
            MATCH (m:Movie)
            WHERE m.title CONTAINS 'Star'
            RETURN count(m) AS c
        """).single()["c"]
        print("Count 2 (inside same tx) =", res2)
        tx.commit()
        print("\nSession A: After commit, new read")
        res3 = session.run("""
            MATCH (m:Movie)
            WHERE m.title CONTAINS 'Star'
            RETURN count(m) AS c
        """).single()["c"]
        print("Count 3 (new tx) =", res3)

def session_b_work():
    time.sleep(2)  # let A start first
    with driver.session(database=DB) as session:
        print("\nSession B: Creating new movie and committing ...")
        session.run("""
            CREATE (:Movie {movieId:9999, title:'Starship X', genres:'Sci-Fi'});
        """)
        print("Session B: Commit done.")

if __name__ == "__main__":
    # run Session A and B concurrently
    t1 = threading.Thread(target=session_a_work)
    t2 = threading.Thread(target=session_b_work)
    t1.start(); t2.start()
    t1.join(); t2.join()
    driver.close()

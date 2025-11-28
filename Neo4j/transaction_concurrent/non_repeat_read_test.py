import threading
import time
from neo4j import GraphDatabase


URI = "neo4j://localhost:7687"
USER = "neo4j"
PASSWORD = "neo4jpassword"
DB = "mridata"


def transaction_one(driver, t1_has_read, t2_has_written):
    """
    This is our "victim" transaction (T1).
    It will read the same data twice and get different results.
    """
    with driver.session(database=DB) as session:
        
        # We must use an explicit transaction to keep it open
        with session.begin_transaction() as tx:
            try:
                # 1. First Read
                result1 = tx.run("MATCH (p:Patient {PatientId: 1}) RETURN p.ClinicalNote AS note")
                value1 = result1.single()['note']
                print(f"[T1] READ 1: Patient 1's Clinical Note: {value1}")
                
                # 2. Signal T2 that it can start its update
                print("[T1] Pausing. Signaling T2 to run...")
                t1_has_read.set()
                
                # 3. Wait for T2 to finish committing its change
                t2_has_written.wait()
                print("[T1] Resumed. T2 has committed its change.")
                
                # 4. Second Read (in the *same* transaction)
                result2 = tx.run("MATCH (p:Patient {PatientId: 1}) RETURN p.ClinicalNote AS note")
                value2 = result2.single()['note']
                print(f"[T1] READ 2: Patient 1's Clinical Note: {value2}")
                
                # 5. The Proof
                if value1 != value2:
                    print("\n!!! NON-REPEATABLE READ DETECTED !!!")
                    print(f"    Within the same transaction, Read 1 got {value1} and Read 2 got {value2}.")
                    print("    This is because T2 committed a change, and our READ_COMMITTED isolation level saw it.")
                else:
                    print("\n--- Anomaly not detected ---")
                    
                # 6. Rollback changes
                string = "{PatientId: 1}"
                tx.run(f"MATCH (p:Patient {string}) SET p.ClinicalNote = '{value1}'")
                
                tx.commit()

            except Exception as e:
                print(f"[T1] Error, rolling back: {e}")
                tx.rollback()

def transaction_two(driver, t1_has_read, t2_has_written):
    """
    This is our "interfering" transaction (T2).
    It waits for T1 to read, then updates the data and commits.
    """
    
    # 1. Wait for T1 to perform its first read
    print("[T2] Waiting for T1 to read first...")
    t1_has_read.wait()
    
    # 2. T1 is now paused. T2 can perform its update.
    print("[T2] T1 is paused. I will now update the clinical's note.")
    
    # We can use a managed transaction (execute_write)
    # as it will BEGIN, RUN, and COMMIT all at once.
    with driver.session(database=DB) as session:
        session.execute_write(update_visits)
        
    print("[T2] Update committed. Signaling T1 to continue.")
    
    # 3. Signal T1 that we are done
    t2_has_written.set()

def update_visits(tx):
    """A helper function for T2's write transaction."""
    tx.run("MATCH (p:Patient {PatientId: 1}) SET p.ClinicalNote = 'Note updated by T2'")


# Main script execution
if __name__ == "__main__":
    
    # Create the single driver instance (thread-safe)
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    
    # 2. Create our synchronization events
    t1_read_event = threading.Event()
    t2_write_event = threading.Event()
    
    # 3. Create the two threads, passing them the events
    t1 = threading.Thread(
        target=transaction_one, 
        args=(driver, t1_read_event, t2_write_event)
    )
    t2 = threading.Thread(
        target=transaction_two, 
        args=(driver, t1_read_event, t2_write_event)
    )
    
    # 4. Start the threads
    print("--- Starting demonstration ---")
    t1.start()
    time.sleep(0.1) # Give T1 a tiny head start
    t2.start()
    
    # 5. Wait for both threads to finish
    t1.join()
    t2.join()
    
    # 6. Clean up
    driver.close()
    print("\n--- Demonstration complete ---")
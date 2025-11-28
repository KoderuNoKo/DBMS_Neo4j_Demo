import threading
import time
import psycopg2
from psycopg2 import extensions

# --- Configuration ---
DB_CONFIG = {
    "dbname": "mridata",
    "user": "postgres",
    "password": "koderu",
    "host": "localhost",
    "port": "5432"
}

# TOGGLE THIS TO SEE THE DIFFERENCE
# 0 = READ COMMITTED (Default, Anomaly occurs - like Neo4j example)
# 1 = REPEATABLE READ (MVCC Snapshot, Anomaly prevented)
USE_REPEATABLE_READ = True

def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

def setup_data():
    """Reset data to a known state before test."""
    conn = get_connection()
    cur = conn.cursor()
    # Ensure patient exists based on schema
    cur.execute("DELETE FROM patient WHERE patient_id = 'P001'")
    cur.execute("""
        INSERT INTO patient (patient_id, age, sex, clinical_note)
        VALUES ('P001', 30, 'M', 'Original Note')
    """)
    conn.commit()
    conn.close()
    print("--- Data Reset: Patient P001 note set to 'Original Note' ---")

def transaction_one(t1_has_read, t2_has_written):
    """
    Victim Transaction (T1).
    Attempts to read data, wait, and read again.
    """
    conn = get_connection()
    
    # Set Isolation Level based on configuration
    if USE_REPEATABLE_READ:
        conn.set_session(isolation_level=extensions.ISOLATION_LEVEL_REPEATABLE_READ)
        level_name = "REPEATABLE READ"
    else:
        conn.set_session(isolation_level=extensions.ISOLATION_LEVEL_READ_COMMITTED)
        level_name = "READ COMMITTED"

    print(f"[T1] Started with isolation: {level_name}")

    try:
        cur = conn.cursor()
        
        # 1. First Read
        cur.execute("SELECT clinical_note FROM patient WHERE patient_id = '1'")
        value1 = cur.fetchone()[0]
        print(f"[T1] READ 1: {value1}")
        
        # 2. Signal T2 to update
        print("[T1] Pausing. Signaling T2...")
        t1_has_read.set()
        
        # 3. Wait for T2
        t2_has_written.wait()
        print("[T1] Resumed. T2 has committed.")
        
        # 4. Second Read (Same transaction)
        cur.execute("SELECT clinical_note FROM patient WHERE patient_id = '1'")
        value2 = cur.fetchone()[0]
        print(f"[T1] READ 2: {value2}")
        
        # 5. The Proof
        if value1 != value2:
            print("\n!!! NON-REPEATABLE READ DETECTED !!!")
            print(f"    T1 saw the update from T2. ({value1} -> {value2})")
            print("    This happens in READ COMMITTED.")
        else:
            print("\n*** PHENOMENON PREVENTED (REPEATABLE READ) ***")
            print(f"    T1 ignored T2's update. ({value1} == {value2})")
            print("    PostgreSQL MVCC provided a consistent snapshot.")
            
        conn.commit()
    except Exception as e:
        print(f"[T1] Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def transaction_two(t1_has_read, t2_has_written):
    """
    Interfering Transaction (T2).
    Updates data while T1 is sleeping.
    """
    conn = get_connection()
    # T2 is a standard transaction, usually Read Committed by default
    conn.set_session(isolation_level=extensions.ISOLATION_LEVEL_READ_COMMITTED)

    try:
        cur = conn.cursor()
        
        # 1. Wait for T1 to start
        t1_has_read.wait()
        
        # 2. Update the data
        print("[T2] Updating patient note...")
        cur.execute("UPDATE patient SET clinical_note = 'Updated by T2' WHERE patient_id = '1'")
        
        # 3. Commit immediately makes it visible to other Read Committed transactions
        conn.commit() 
        print("[T2] Update committed. Signaling T1.")
        
        t2_has_written.set()
    except Exception as e:
        print(f"[T2] Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    setup_data()
    
    # Create synchronization events
    t1_read_event = threading.Event()
    t2_write_event = threading.Event()
    
    t1 = threading.Thread(target=transaction_one, args=(t1_read_event, t2_write_event))
    t2 = threading.Thread(target=transaction_two, args=(t1_read_event, t2_write_event))
    
    t1.start()
    time.sleep(0.1) 
    t2.start()
    
    t1.join()
    t2.join()
    print("\n--- Experiment Complete ---")
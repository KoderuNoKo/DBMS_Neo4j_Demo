import threading
import psycopg2
import time
from datetime import datetime

# --- CONFIGURATION ---
# Update these credentials to match your local PostgreSQL instance
DB_CONFIG = {
    "dbname": "mridata",
    "user": "postgres",
    "password": "koderu",
    "host": "localhost",
    "port": "5432"
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def log(thread_name, message):
    """Helper to print messages with precise timestamps."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}][{thread_name}] {message}")

# def setup_database():
#     """
#     Resets the table and inserts a test record based on your schema.
#     """
#     conn = get_connection()
#     cur = conn.cursor()
    
#     # Using the schema definition provided in postgres_schema.md
#     create_table_sql = """
#     CREATE TABLE IF NOT EXISTS patient (
#         patient_id VARCHAR(255) PRIMARY KEY,
#         age INTEGER,
#         sex VARCHAR(10),
#         size FLOAT,
#         weight FLOAT,
#         patient_identity_removed BOOLEAN,
#         deidentification_method VARCHAR(255),
#         birthdate DATE,
#         clinical_note TEXT
#     );
#     """
    
#     try:
#         cur.execute(create_table_sql)
#         # Clean up previous test data
#         cur.execute("DELETE FROM patient WHERE patient_id = 'TEST_PATIENT_001';")
#         # Insert a fresh test patient
#         cur.execute("""
#             INSERT INTO patient (patient_id, age, sex, clinical_note)
#             VALUES ('TEST_PATIENT_001', 30, 'M', 'Initial Note');
#         """)
#         conn.commit()
#         print("--- Database Setup Complete: Test Patient Created ---\n")
#     except Exception as e:
#         print(f"Setup Error: {e}")
#         conn.rollback()
#     finally:
#         conn.close()

def update_patient_note(thread_name, patient_id, new_note, sleep_time):
    """
    Connects to DB, attempts to update a row, holds the transaction open 
    (sleeping), and then commits.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        log(thread_name, "Connecting and starting transaction...")

        # The UPDATE statement attempts to acquire a ROW EXCLUSIVE LOCK
        query = f"UPDATE patient SET clinical_note = %s WHERE patient_id = '{patient_id}'"
        
        log(thread_name, "Attempting to acquire lock and update...")
        cur.execute(query, (new_note,))
        
        # If we reach here, we successfully acquired the lock
        log(thread_name, f"UPDATE executed. Holding lock for {sleep_time} seconds...")
        
        # Simulate a long process (e.g., user thinking, complex calculation)
        time.sleep(sleep_time)
        
        conn.commit()
        log(thread_name, "Transaction Committed. Lock released.")

    except Exception as e:
        log(thread_name, f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def run_concurrency_test():
    # setup_database()

    # Thread 1: Updates the note and sleeps for 5 seconds (holding the lock)
    t1 = threading.Thread(
        target=update_patient_note, 
        args=("THREAD_A (Slow)", 1, "Updated by Thread A", 5)
    )

    # Thread 2: Updates the note and sleeps for 0 seconds.
    # It starts 1 second after T1, ensuring T1 already has the lock.
    t2 = threading.Thread(
        target=update_patient_note, 
        args=("THREAD_B (Fast)", 1, "Updated by Thread B", 0)
    )

    t1.start()
    time.sleep(1) # Ensure Thread A gets the lock first
    t2.start()

    t1.join()
    t2.join()
    
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    run_concurrency_test()
import threading, time, random
from neo4j import GraphDatabase, exceptions

import argparse

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "neo4jpassword")
DB_NAME = "movielens"
driver = GraphDatabase.driver(URI, auth=AUTH, max_connection_lifetime=1000)

MOVIE_ID = 1

def inc_view(tx, movie_id):
    tx.run("""
        MATCH (m:Movie {movieId:$id})
        SET m.viewCount = coalesce(m.viewCount,0) + 1
        RETURN m.viewCount AS viewCount
    """, id=movie_id)
    
def worker(thread_id, runs_num, shared_session=None):
    """Each worker performs 'runs' write tx to increment the viewCount."""
    local_session = shared_session or driver.session(database=DB_NAME)
    for i in range(runs_num):
        t0 = time.time()
        try:
            local_session.execute_write(inc_view, MOVIE_ID)
            status = "OK"
        except exceptions.TransientError as e:
            status = "TransientError"
        except Exception as e:
            status = f"Error:{type(e).__name__}"
            
        # report execution timestamp and duration
        latency = round((time.time()-t0)*1000, 2)
        print(f"Thread {thread_id:02d} Iter {i:03d}: {status} ({latency} ms)")
        # simulate delay
        time.sleep(random.random()*0.05)
    
    if shared_session is None:
        local_session.close()
        
def run_test(n_threads, n_runs, is_shared_session=False):
    print(f"\n=== Running with {'SHARED' if is_shared_session else 'INDIVIDUAL'} sessions ===")
    thread_lst = []
    shared_session = driver.session(database=DB_NAME) if is_shared_session else None
    
    for t in range(n_threads):
        th = threading.Thread(target=worker, args=(t, n_runs, shared_session))
        th.start()
        thread_lst.append(th)
        
    for th in thread_lst:
        th.join()
        
    if shared_session:
        shared_session.close()
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_threads", type=int, help="Number of threads")
    parser.add_argument("--n_runs", type=int, help="Number of runs a single threads will perform")
    parser.add_argument("--share_session", action="store_true", help="Decide whether all threads share the same session")
    args = parser.parse_args()
    run_test(args.n_threads, args.n_runs, args.share_session)

driver.close()
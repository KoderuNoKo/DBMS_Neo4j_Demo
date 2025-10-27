# Neo4j Transactions & Concurrency

- To maintain data integrity and ensure reliable transactional behavior, Neo4j DBMS supports transactions with full ACID properties, and it uses a write-ahead transaction log to ensure durability [1].


## Atomicity — commit & rollback

**Procedure:**
1. Start a transaction (Cypher or driver).
2. Create a node and relationship
3. During which process, insert an fail operation that will roll back the transaction — show node is absent.
4. Repeat without the fail operation — show node persists.

```cypher
CREATE (n1:TempTest {name:'t1', value: 1})
CREATE (n2:TempTest {name:'t2', value: 2})
CREATE (n3:TempTest {name:'t3', value: 1/0}) // this will fail
CREATE (n4:TempTest {name:'t4', value: 4})
```

```cypher
MATCH (n:TempTest) RETURN n;
```
=> "No changes, no records"

## Currency & Isolation — Single-node concurrent write conflict (lost-update / write lock)

- **Procedure:** 
	- Run n concurrent clients trying to increment a `viewCount` property on the same `Movie` node (or add relationships from two sessions to same node). Showing that updates still happens consistently  `./neo4j_script/concurrent_test.py`
	- Showing the Neo4j Deadlock handle mechanism `./neo4j_script/transient_test.py`

## Non-repeatable reads [2]

- A single transaction in Neo4j can read the _exact same piece of data_ twice and get two _different_ values.

- This anomaly is possible due to Neo4j's default `READ_COMMITTED` isolation level, which allows a transaction to see changes that have been committed by _other_ transactions, even while the original transaction is still in progress.

- **Procedure** `./neo4j_script/non_repeat_read_2.py`
	- **Thread 1 (T1)** will read a user's visit count, pause, and then read it again, all within _one_ long-running transaction.
	- **Thread 2 (T2)** will jump in during T1's pause to update and _commit_ a new visit count for that same user.

# Reference

[1] Neo4j, "Database Internals", Neo4j Operations Manual. [Online]. Available: https://neo4j.com/docs/operations-manual/current/database-internals/. [Accessed: Oct. 6, 2025].

[2] Neo4j, "Non-repeatable reads", Neo4j Operations Manual. [Online]. Available: [https://neo4j.com/docs/operations-manual/current/database-internals/concurrent-data-access/#_non_repeatable_reads](https://neo4j.com/docs/operations-manual/current/database-internals/concurrent-data-access/#_non_repeatable_reads). [Accessed: Oct. 6, 2025].
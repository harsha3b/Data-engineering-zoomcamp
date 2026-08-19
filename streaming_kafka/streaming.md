# Streaming Data Engineering: Core Concepts

A trainer-style guide to streaming, the generic pipeline shape, and how producers, brokers, and consumers work underneath.

---

## 1. What is streaming?

Everything you've likely done before this — dbt models, Spark/Dataproc batch jobs, dlt pipelines — is **batch processing**: data piles up somewhere, and on a schedule (hourly, daily) a job runs and processes the whole pile at once. That's fine when "a few hours old" is an acceptable answer.

**Streaming** is for the cases where it isn't: instead of "data lands, then later I read all of it," it's "each event is pushed to me the instant it exists, and I react to it as it arrives."

### Real-life example: a bank

- **Batch approach**: every night at 1 AM, a job runs over all of that day's transactions, updates account balances, and generates statements. If a stolen card gets swiped 200 times at 3 PM, nobody notices until the batch job runs — hours later.
- **Streaming approach**: every card swipe is an *event*. The moment it happens, it's pushed into a pipeline that checks it for fraud patterns in real time. A block can happen within milliseconds of a suspicious swipe, not after the fact.

Same underlying data (transactions), completely different processing model: **finite pile processed periodically** vs. **continuous, unbounded flow processed as it happens**.

Other everyday examples of streaming systems: a ride-hailing app updating your driver's live location, a stock ticker, a factory sensor triggering an alarm the instant a machine overheats, a live sports score feed.

---

## 2. The generic shape of a streaming pipeline

Every streaming system, no matter the tools, is built from the same four roles:

```
Producer → Broker (Kafka/Redpanda) → Stream Processor (consumer logic) → Sink
```

- **Producer**: something generating events (an app, a sensor, an API) and pushing them out.
- **Broker**: a durable buffer sitting between producers and consumers, so neither needs to know about or wait on the other.
- **Stream processor / consumer**: reads events off the broker and does work with them — logging, transforming, aggregating.
- **Sink**: where the processed result ends up — a database, a warehouse, a dashboard.

### Real-life analogy: a restaurant kitchen

Imagine a restaurant with waiters, an order rail, cooks, and a pass-through window to the dining room:

| Streaming role | Restaurant equivalent |
|---|---|
| **Producer** | Waiter — writes down an order the moment a customer gives it |
| **Broker** | The order rail — a physical strip where order tickets are clipped in the order they came in, waiting to be picked up |
| **Stream processor / consumer** | The cook — pulls the next ticket off the rail and prepares that dish |
| **Sink** | The pass-through window — the finished plate goes here, ready for the customer |

The waiter doesn't hand the order directly to a specific cook and wait for them to be free — they clip it to the rail and move on to the next table. Cooks work through the rail at their own pace, pulling tickets when they're ready. This **decoupling** — producer and consumer never talking to each other directly, both interacting only with the rail in between — is the entire point of a broker.

---

## 3. Scheduling vs. streaming

A common early misconception: picturing a streaming consumer that wakes up every minute, grabs what's arrived, processes it, then goes back offline — essentially a batch job with a very short interval. This is worth naming clearly, because it's a different model from how a real streaming consumer behaves.

| | Batch (scheduled) | Streaming |
|---|---|---|
| **When it runs** | Wakes up on a schedule (hourly, daily, or even every minute), does work, exits | Runs continuously, never intentionally stops |
| **What it processes** | A finite, known chunk of data accumulated since last run | One event (or small micro-batch) at a time, as it arrives |
| **Mental model** | "Check the mailbox once an hour" | "Sit by the door and answer it the instant someone knocks" |

A real streaming consumer stays connected and continuously polls for new messages, conceptually:

```python
while True:
    messages = consumer.poll()
    process(messages)
```

It never intentionally goes offline. The reason this still feels forgiving in practice — a consumer can crash, be redeployed, or simply not be running yet without losing anything — comes down to the broker's **retention** (covered below), not a scheduling behavior. That's a resilience feature of a continuously-running process, not its designed operating rhythm.

One caveat worth knowing: some frameworks (Spark Structured Streaming, in its default mode) actually do implement **micro-batching** — polling on a fixed short interval and processing small batches. So the "batch on a tight schedule" model isn't wrong everywhere, it's just not how a plain Kafka consumer or PyFlink's default mode works.

---

## 4. Producers

### What a producer is

A producer is anything that generates events and pushes them into the broker. It's the source side of the pipeline — a web application logging clicks, a payment service emitting transaction events, an IoT sensor reporting a reading, or a script pulling from an API and forwarding each record.

### How it connects to a real application or service

In practice, a producer is usually not a standalone thing — it's a small piece of logic embedded *inside* an existing application or service. For example:
- An e-commerce checkout service, right after confirming an order, also sends an `"order_placed"` event to a broker — the checkout flow itself is the producer.
- A mobile app's backend emits a `"user_signed_up"` event the moment a new account is created.

The producer doesn't need to know who's going to consume that event or what they'll do with it — it just needs to know the broker's address and the shape of the message it's sending. This is the decoupling from Section 2 in action: the checkout service's job ends the moment the event is handed off.

### How it sends data — the mechanics

1. **Connect** to the broker using its address (e.g., `bootstrap_servers`) — this is the entry point; the client then learns about the rest of the cluster from there.
2. **Serialize** the event — convert it from an in-memory object (a class instance, a dict) into bytes, since the broker only understands bytes. JSON and Avro are common formats for this.
3. **Send** the message to a specific **topic** (and optionally a partition, or a key that determines the partition — see Section 5).
4. The client library typically buffers messages internally and transmits them in batches in the background for efficiency, rather than making one network round-trip per message. A `flush()` (or equivalent) call blocks until everything buffered has actually been transmitted and acknowledged — important to call before a producer process exits, so nothing sitting in the buffer gets silently lost.

### Key producer terminology

- **Message key** (optional): used to decide which partition a message goes to, and to guarantee all messages with the same key land in the same partition, in order (e.g., keying by `user_id` so all of one user's events stay ordered).
- **Serializer**: the function/logic that converts an application object into bytes before sending.
- **Acknowledgment (`acks`)**: how strictly the producer waits for confirmation that the broker actually received and durably stored the message before considering the send successful. Ranges from "don't wait at all" (fastest, riskiest) to "wait until replicated to multiple brokers" (slowest, safest).

> **Single-node setup note**: On a local single-broker Redpanda/Kafka container, the producer only ever has one broker address to connect to, and `acks` settings around replication don't have much effect since there's nothing to replicate to. In a **production, multi-broker cluster**, the producer's `bootstrap_servers` typically lists several broker addresses (for resilience if one is down), and `acks` becomes a genuine durability-vs-latency tradeoff, since messages can be replicated across multiple brokers before being acknowledged.

---

## 5. Brokers

### What a broker is

The broker is the durable, always-on middleman that receives messages from producers, stores them, and serves them to consumers. Kafka is the industry-standard implementation; Redpanda is a lighter-weight, Kafka-API-compatible alternative often used for local development.

### Real-life analogy: a library's returns ledger

Picture a large public library. Every returned book gets logged into a big ledger, in the exact order it was handed in — book 1, book 2, book 3, and so on, forever. The ledger is never edited or reordered; new entries are only ever added to the end. Different staff members can each keep their own personal bookmark showing how far down the ledger they've reviewed, and they can each work through it independently, at their own pace, without disturbing the ledger or each other.

### Core terminology

**Topic**
A named category of messages — e.g., `orders`, `clicks`, `sensor-readings`. Producers send to a topic; consumers subscribe to one.

**Log**
The actual storage structure underneath a topic. A log is an append-only sequence of messages — new messages are only ever added to the end, never inserted or edited in the middle.

**Partition**
A topic is split into one or more partitions, and each partition is its own independent, ordered log. Splitting a topic this way is what allows parallelism: each partition can be actively read by only one consumer within a given consumer group at a time, so more partitions means more consumers can work in parallel. Messages are assigned to a partition either by a producer-supplied key (guaranteeing order per key) or round-robin if no key is given.

**Offset**
Within a single partition, every message gets a sequential number the moment it's appended — 0 for the first message ever written to that partition, 1 for the next, and so on, forever increasing. This is purely a position marker within one partition's log, not a global identifier across the whole topic.

**Replication**
Each partition's log can be copied across multiple brokers, so if one broker fails, another still holds the data. One broker is designated the **leader** for a given partition (handling all reads/writes for it); others hold **replicas** that stay in sync in case the leader goes down.

### Why data is written to permanent storage

This is a deliberate design choice, not an incidental detail:

- **Durability**: if the broker process restarted or crashed, in-memory-only data would simply vanish. Writing to disk means messages survive broker restarts.
- **Decoupling producer and consumer speed**: a producer can send messages far faster than a consumer processes them (or vice versa) without either being blocked — the disk log absorbs the difference. A slow or temporarily offline consumer doesn't back up or block the producer.
- **Replayability**: because messages aren't deleted the moment they're read, multiple independent consumers can read the same data at different times, and a consumer can be restarted and told to re-read from an earlier point if needed (e.g., after a bug fix, to reprocess data correctly).
- **Retention window**: data isn't kept forever by default — a configurable retention period (commonly 7 days, but tunable per topic) controls how long messages stay on disk before being eligible for deletion. This balances "keep enough history to be useful and safe" against unbounded disk growth.

Performance-wise, the OS page cache (RAM) is used to speed up reads and writes, but this is an optimization layer — the durable source of truth is always the on-disk log, not memory.

### Other important broker functions

- **Cluster coordination**: brokers in a cluster need to agree on who's the leader for each partition, track cluster membership, and detect failures. (Historically Kafka used ZooKeeper for this; newer versions and Redpanda handle this internally via their own consensus protocols.)
- **Serving reads efficiently**: brokers are optimized for sequential disk reads, since consumers typically read a partition's log in order — this is part of why the append-only log design performs well even at high volume.

> **Single-node setup note**: A local single-broker Redpanda container (like in a typical docker-compose setup) still has topics, partitions, logs, and offsets — all core concepts fully apply. What's absent is meaningful **replication**, since there's only one broker to hold data; if that container goes down, the data goes with it. In a **production, multi-broker cluster**, a topic's partitions are spread across multiple broker machines, each partition has a leader plus replicas on other brokers, and the cluster can tolerate a broker failing without losing data or availability.

---

## 6. Consumers

### What a consumer is

A consumer is anything that reads messages from a broker's topic and does something with them — the "cook pulling tickets off the rail" from the restaurant analogy. This can be as simple as a script printing messages to a console, or as complex as a stream-processing engine (PyFlink) performing windowed aggregations.

### How it interacts with the broker

A consumer doesn't ask the broker to "send me everything" — it operates on a pull model, one message (or small batch) at a time:

1. **Connect and subscribe** to one or more topics.
2. **Poll** for the next unread message(s) at its current offset position.
3. **Process** each message (deserialize the bytes back into a usable object, then do whatever work is needed).
4. **Commit** its offset back to the broker periodically, marking progress.
5. Loop back to step 2, indefinitely — this is the long-running, always-on behavior discussed in Section 3.

### Consumer groups

A **consumer group** is a name that the broker uses to track "how far has *this* group read?" After processing messages, a consumer commits its current offset back to the broker under its group's name — that bookmark lives on the broker itself, not in the consumer's own code or machine.

**Real-life parallel**: two different staff members, "Fraud Review" and "Inventory Audit," might both read through the same returns ledger independently. Each keeps their own separate bookmark. One being three days behind doesn't affect the other at all — they're reading the same ledger, at their own pace, tracked separately.

Practical consequences:
- Same `group_id`, restarted → resumes exactly where it left off, picking up from the saved offset.
- A brand-new `group_id` → the broker has no bookmark for it yet, so it must decide where to start (see `auto_offset_reset` below).
- Two different `group_id`s reading the same topic → two fully independent readers (e.g. a "console logger" and a "database writer") consuming the same topic without interfering with each other.
- Within a single group, if there are multiple partitions, Kafka can spread them across multiple consumer instances in that group for parallel processing — each partition still only actively read by one consumer within the group at a time.

### Offsets, from the consumer's side

The offset is the mechanism that makes "resume where I left off" possible at all. Since it's just a number — a position in one partition's log — committing it is cheap, and resuming from it is exact: no missed messages, no reprocessing duplicates (barring edge cases around commit timing, which is its own deeper topic).

### `auto_offset_reset` — where to start with no bookmark yet

This setting only matters the first time a `group_id` has no committed offset stored. It answers: "since I have nothing to resume from, where do I begin?"

- `'earliest'` — start from offset 0, the oldest retained message. You get full history still on disk.
- `'latest'` — start from "now." You only see messages produced *after* you connect; anything already on the broker is skipped.

**Real-life parallel**: a new staff member joining the ledger review team can either be told "start from page 1 and work through everything ever logged" (`earliest`), or "don't worry about the backlog, just start noting down whatever comes in from today onward" (`latest`).

Once a group has a saved bookmark, `auto_offset_reset` is ignored entirely — the broker just resumes from the saved offset, regardless of this setting.

### Deserialization

The mirror image of a producer's serializer: a function registered on the consumer that automatically converts each message's raw bytes back into a usable object (e.g., bytes → JSON string → dict → a typed class instance) before your processing code ever sees it. Registering it once at consumer setup means every message is transparently converted, without needing to call the conversion function manually at every step.

> **Single-node setup note**: On a local single-broker setup, consumer groups and offsets work exactly as described — there's just one broker holding everything, so there's no question of "which broker do I read from." In a **production, multi-broker cluster**, a consumer group's members can be spread across multiple machines, each handling a subset of the topic's partitions, and the broker cluster (not just one machine) is responsible for tracking each group's offsets reliably even if individual brokers fail.
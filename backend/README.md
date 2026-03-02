# Python Recursive DNS Resolver

This is a simplified, yet fully functional, recursive DNS resolver written in pure Python. It demonstrates lower-level network communication, DNS packet structure parsing, recursive resolution, and caching.

## Features Let's Create!

- **Recursive Resolution**: Traces requests from Root DNS servers -> TLD servers -> Authoritative servers down to the final answer.
- **Support Multiple Record Types**: Can parse and request `A`, `AAAA`, `MX`, `NS`, and `CNAME` records.
- **In-Memory Caching**: Resolves instantly if a query is cached. Honors proper Time-To-Live (TTL) provided by DNS responses.
- **Cache Expiry**: Background thread purges expired records periodically.
- **Multithreading Ready**: Supports multithreaded architecture through `concurrent.futures`. Resolves domain queries in threads for non-blocking I/O.
- **Interactive CLI**: Simple CLI tool to explore domains interactively.
- **Logging**: Detailed debug logging tracking the delegation tree step-by-step.

## Setup and Execution

### Requirements
- Python 3.6+
- No external dependencies are needed (built entirely on standard libraries: `socket`, `struct`, `threading`, `logging`).

### Running the Resolver

Run the `resolver.py` directly to start the interactive loop:

```bash
cd /home/hithx/Documents/DNS-resolver
python resolver.py
```

### Supported Commands

When inside the interactive prompt, type the domain followed optionally by the record type (`A`, `AAAA`, `MX`):

```text
Enter query (domain [type]): google.com
Enter query (domain [type]): google.com AAAA
Enter query (domain [type]): gmail.com MX
```

Type `exit` or `quit` to stop the application.

### Architecture

1. **`utils.py`**: Configures safe multithread logging tracking resolution.
2. **`dns_message.py`**: Byte-packs the headers and queries, unpacking arbitrary length compression DNS responses. 
3. **`cache.py`**: Dictionary with a lock mechanism to safely read, store, and thread-cull expired TTL records.
4. **`resolver.py`**: The driver logic containing I/O socket configurations, iterative fallback loops (looking for Glue Records vs independent NS resolving), and handling CNAME follows.

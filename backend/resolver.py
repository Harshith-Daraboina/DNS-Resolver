import socket
import select
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from dns_message import DNSQueryBuilder, DNSParser, TYPE_A, TYPE_AAAA, TYPE_MX, TYPE_NS, TYPE_CNAME
from cache import cache
from utils import logger
import struct

# Root servers provided by IANA
ROOT_SERVERS = [
    "198.41.0.4",      # a.root-servers.net
    "199.9.14.201",    # b.root-servers.net
    "192.33.4.12",     # c.root-servers.net
    "199.7.91.13",     # d.root-servers.net
]

DNS_PORT = 53
TIMEOUT = 5

class Resolver:
    def __init__(self):
        # We use a thread pool to allow async-like querying if needed
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.logs = []

    def log(self, message: str, level: str = "INFO"):
        self.logs.append(f"{level}: {message}")
        if level == "DEBUG":
            logger.debug(message)
        elif level == "INFO":
            logger.info(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)

    def query(self, domain: str, server: str, record_type: int) -> Optional[dict]:
        """Sends a DNS query to a server using UDP."""
        self.log(f"Querying {server} for {domain} (Type: {record_type})", "DEBUG")
        
        query_bytes = DNSQueryBuilder.build_query(domain, record_type)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(TIMEOUT)
        
        try:
            sock.sendto(query_bytes, (server, DNS_PORT))
            
            # Wait for response with select (more robust)
            ready = select.select([sock], [], [], TIMEOUT)
            if ready[0]:
                data, _ = sock.recvfrom(4096)
                parser = DNSParser(data)
                return parser.parse()
            else:
                self.log(f"Timeout (select) querying {server} for {domain}", "WARNING")
        except socket.timeout:
            self.log(f"Timeout (socket) querying {server} for {domain}", "WARNING")
        except Exception as e:
            self.log(f"Error querying {server}: {e}", "ERROR")
        finally:
            sock.close()
            
        return None

    def resolve(self, domain: str, record_type: int = TYPE_A) -> List[dict]:
        """Resolves a domain iteratively starting from ROOT_SERVERS."""
        self.log(f"Resolving {domain} for record type {record_type}", "INFO")
        
        # Check cache first
        cached_records = cache.get(domain, record_type)
        if cached_records:
            self.log(f"Returned {len(cached_records)} cached records for {domain}", "INFO")
            return cached_records

        # Start with a root server
        current_servers = ROOT_SERVERS.copy()
        
        visited_cnames = set()
        
        while current_servers:
            # Pick the first available server
            server_ip = current_servers.pop(0)
            target_domain = domain
            
            response = self.query(target_domain, server_ip, record_type)
            if not response:
                continue
                
            # If we got the authoritative answer
            if response['answers']:
                answers = response['answers']
                
                # Check for CNAME in answers if we aren't specifically looking for it
                if record_type != TYPE_CNAME:
                    cname_records = [a for a in answers if a['type'] == TYPE_CNAME]
                    if cname_records:
                        cname = cname_records[0]['data']
                        self.log(f"Found CNAME for {domain} -> {cname}. Following alias...", "INFO")
                        
                        if cname in visited_cnames:
                            self.log(f"CNAME loop detected involving {cname}", "ERROR")
                            return []
                        visited_cnames.add(cname)
                        
                        # Cache the CNAME record itself optionally
                        cache.set(domain, TYPE_CNAME, cname_records)
                        
                        # Resolve the actual target and return
                        resolved = self.resolve(cname, record_type)
                        # We should ideally cache the final target against the original domain, but for simplicity
                        # returning the resolved items is sufficient
                        return resolved

                # Cache and return actual answers
                cache.set(domain, record_type, answers)
                self.log(f"Successfully resolved final answer from {server_ip}", "INFO")
                return answers
                
            # Look for Name Servers (NS) in authorities to delegate
            if response['authorities']:
                ns_records = [auth for auth in response['authorities'] if auth['type'] == TYPE_NS]
                
                # Try to find Glue records (A/AAAA) in additionals for those NS records
                glue_ips = []
                for ns in ns_records:
                    ns_name = ns['data']
                    for add in response['additionals']:
                        if add['name'] == ns_name and add['type'] == TYPE_A:
                            glue_ips.append(add['data'])
                            # Precache the glue records for future use
                            cache.set(ns_name, TYPE_A, [add])
                            
                if glue_ips:
                    self.log(f"Delegating to next servers using Glue IPs: {glue_ips}", "DEBUG")
                    current_servers = glue_ips
                    continue
                elif ns_records:
                    # We have NS but no glue (A) IPs, we must resolve the NS name first
                    ns_name = ns_records[0]['data']
                    self.log(f"No Glue records found. Required to resolve NS {ns_name} first.", "DEBUG")
                    ns_ips = self.resolve(ns_name, TYPE_A)
                    if ns_ips:
                        current_servers = [ip_rec['data'] for ip_rec in ns_ips]
                        continue
                        
            # If we get here, no progress was made via this server
            self.log(f"Server {server_ip} did not provide useful NS or Answers.", "WARNING")
            
        self.log(f"Failed to resolve {domain}. All servers exhausted or timed out.", "ERROR")
        return []

def print_results(domain: str, record_type_name: str, records: List[dict]):
    if not records:
        print(f"\nNo records found for {domain} ({record_type_name})")
        return
        
    print(f"\nResults for {domain} ({record_type_name}):")
    print("-" * 50)
    for rec in records:
        data = rec['data']
        ttl = rec['ttl']
        if isinstance(data, dict) and 'preference' in data: # MX
            print(f"[{ttl}s] MX  {data['preference']} {data['exchange']}")
        else:
            print(f"[{ttl}s] {record_type_name}   {data}")
    print("-" * 50)

def cli():
    resolver = Resolver()
    type_map = {
        'A': TYPE_A,
        'AAAA': TYPE_AAAA,
        'MX': TYPE_MX,
        'NS': TYPE_NS,
        'CNAME': TYPE_CNAME
    }
    
    print("Welcome to the Python Recursive DNS Resolver!")
    print("Example commands: 'google.com', 'google.com AAAA', 'gmail.com MX'")
    print("Type 'exit' or 'quit' to terminate.\n")
    
    while True:
        try:
            line = input("Enter query (domain [type]): ").strip()
            if not line:
                continue
                
            if line.lower() in ('exit', 'quit'):
                break
                
            parts = line.split()
            domain = parts[0]
            record_type_str = parts[1].upper() if len(parts) > 1 else 'A'
            
            record_type = type_map.get(record_type_str)
            if not record_type:
                print(f"Unsupported record type: {record_type_str}")
                continue
                
            # Submit to thread pool (multithreading requirement)
            future = resolver.executor.submit(resolver.resolve, domain, record_type)
            results = future.result() # Wait for results
            
            print_results(domain, record_type_str, results)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    cli()

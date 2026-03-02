import struct
import random
from utils import logger
from typing import Dict, List, Tuple, Any

# Record Types
TYPE_A = 1
TYPE_NS = 2
TYPE_CNAME = 5
TYPE_MX = 15
TYPE_AAAA = 28

# Record Classes
CLASS_IN = 1

class DNSQueryBuilder:
    @staticmethod
    def build_query(domain: str, record_type: int = TYPE_A) -> bytes:
        # 16-bit identifier
        transaction_id = random.randint(0, 65535)

        # Flags (Standard query, Recursion Desired but we are doing recursion ourselves here, 
        # so we can send 0x0100 just to be safe or 0x0000)
        flags = 0x0000 
        
        questions = 1
        answer_rr = 0
        authority_rr = 0
        additional_rr = 0

        header = struct.pack(
            "!HHHHHH",
            transaction_id,
            flags,
            questions,
            answer_rr,
            authority_rr,
            additional_rr
        )

        qname = b''
        for part in domain.split("."):
            if part:
                qname += struct.pack("B", len(part))
                qname += part.encode()
        qname += b'\x00'

        qclass = CLASS_IN
        question = qname + struct.pack("!HH", record_type, qclass)

        return header + question


class DNSParser:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def parse(self) -> Dict[str, Any]:
        result = {}
        
        # Parse Header (12 bytes)
        req_id, flags, q_count, ans_count, auth_count, add_count = struct.unpack("!HHHHHH", self.data[:12])
        self.offset = 12
        
        result['transaction_id'] = req_id
        result['flags'] = flags
        
        # Is authoritative answer?
        result['aa'] = (flags >> 10) & 1

        # Parse Question Section
        result['questions'] = []
        for _ in range(q_count):
            qname = self._parse_name()
            qtype, qclass = struct.unpack("!HH", self.data[self.offset:self.offset+4])
            self.offset += 4
            result['questions'].append({'name': qname, 'type': qtype, 'class': qclass})

        # Parse Answer Section
        result['answers'] = self._parse_records(ans_count)
        result['authorities'] = self._parse_records(auth_count)
        result['additionals'] = self._parse_records(add_count)
        
        # logger.debug(f"Parsed DNS Response: ID {req_id}, {ans_count} Ans, {auth_count} Auth, {add_count} Add")
        return result

    def _parse_records(self, count: int) -> List[Dict[str, Any]]:
        records = []
        for _ in range(count):
            name = self._parse_name()
            rtype, rclass, ttl, rdlength = struct.unpack("!HHIH", self.data[self.offset:self.offset+10])
            self.offset += 10
            
            rdata = self.data[self.offset:self.offset+rdlength]
            parsed_data = self._parse_rdata(rtype, rdata, self.offset)
            
            self.offset += rdlength
            records.append({
                'name': name,
                'type': rtype,
                'class': rclass,
                'ttl': ttl,
                'data': parsed_data
            })
        return records

    def _parse_rdata(self, rtype: int, rdata: bytes, current_offset: int) -> Any:
        if rtype == TYPE_A:
            return ".".join(map(str, rdata))
        elif rtype == TYPE_AAAA:
            parts = [rdata[i:i+2].hex() for i in range(0, 16, 2)]
            return ":".join(parts)
        elif rtype in (TYPE_NS, TYPE_CNAME):
            temp_offset = self.offset
            self.offset = current_offset
            name = self._parse_name()
            self.offset = temp_offset
            return name
        elif rtype == TYPE_MX:
            # First 2 bytes are preference, then name
            preference = struct.unpack("!H", rdata[:2])[0]
            temp_offset = self.offset
            self.offset = current_offset + 2
            name = self._parse_name()
            self.offset = temp_offset
            return {'preference': preference, 'exchange': name}
        
        return rdata

    def _parse_name(self) -> str:
        parts = []
        jumped = False
        original_offset = self.offset

        while True:
            length = self.data[self.offset]
            if length == 0:
                self.offset += 1
                break
            
            # Check for compression (top 2 bits set to 11)
            if (length & 0xC0) == 0xC0:
                pointer = struct.unpack("!H", self.data[self.offset:self.offset+2])[0]
                pointer &= 0x3FFF
                if not jumped:
                    original_offset = self.offset + 2
                self.offset = pointer
                jumped = True
            else:
                self.offset += 1
                parts.append(self.data[self.offset:self.offset+length].decode('utf-8'))
                self.offset += length

        if jumped:
            self.offset = original_offset
            
        return ".".join(parts)

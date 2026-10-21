"""Full English class lookup for the assembled name/class heading only."""
import struct
from runtime_text import CODE_BASE,branch,instruction,load_address

SITE=0x107a54
GETTER=0x51c2c
TABLE=0x450e30
CLASS_IDS=('X0184','X0017','X0018','X0185','X0186','X0176','X0187',
           'X0188','X0189','X0190','X0191','X0192','X0019')
GETTER_BYTES=bytes.fromhex('812288f0786317647c69182e4e800020')
CONTEXT_ADDRESS=0x107a44
CONTEXT=bytes.fromhex('4bf44df960000000786306207bbd00204bf4a1d9600000007b8500208082b088786600207fa3eb7848179d4560000000')


def collect(original,sources,english):
    rows=[]
    for index,key in enumerate(CLASS_IDS):
        address=struct.unpack_from('>I',original,TABLE-0x10000+4*index)[0]
        row=sources[key]
        if row['source']!='executable' or address not in {o['address'] for o in row['occurrences']}:
            raise ValueError('Full class table source mismatch: '+key)
        text=english[key]['en']
        if not isinstance(text,str) or not text or '\0' in text:
            raise ValueError('Missing full English class name: '+key)
        rows.append(dict(id=key,en=text))
    return rows


def append_code(original,code,table_address,rows):
    for address,expected in ((GETTER,GETTER_BYTES),(CONTEXT_ADDRESS,CONTEXT),
                             (0x409b00,b'%s / %s\0')):
        if original[address-0x10000:address-0x10000+len(expected)]!=expected:
            raise ValueError('Class heading context mismatch at '+hex(address))
    if [r['id'] for r in rows]!=list(CLASS_IDS) or table_address%4:
        raise ValueError('Class heading table mismatch')
    stub=CODE_BASE+len(code)
    # Same leaf lookup as the original getter, using the heading's immutable
    # English table. Only r3/r9 change; CR, LR, TOC and the stack are preserved.
    code.extend(b''.join(instruction(w) for w in load_address(9,table_address)))
    code.extend(GETTER_BYTES[4:])
    code.extend(b'\0'*(-len(code)%16))
    return [(SITE-0x10000,instruction(branch(SITE,stub,True)))],dict(
        site=hex(SITE),stub=hex(stub),table_address=hex(table_address),classes=rows,
        native_getter_unchanged=True,fixed_copy_class_labels_unchanged=True,
        character_name_and_format_unchanged=True,updated_ingame_verification=False)

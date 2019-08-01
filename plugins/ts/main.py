from table import Table
from bitstream import BitStream

def program_association_section(d:Table, bs:BitStream):
    d.add_field('table_id', bs.read_bits, count=8)
    d.add_field('section_syntax_indicator', bs.read_bits, count=1)
    d.add_field('0', bs.read_bits, count=1)
    d.add_field('reserved', bs.read_bits, count=2)
    d.add_field('section_length', bs.read_bits, count=12)
    d.add_field('transport_stream_id', bs.read_bits, count=16)
    d.add_field('reserved', bs.read_bits, count=2)


def transport_packet(d, bs):
    d.add_field('sync_byte', bs.read_bits, count=8)
    d.add_field('transport_error_indicator', bs.read_bits, count=1)
    d.add_field('payload_unit_start_indicator', bs.read_bits, count=1)
    d.add_field('transport_priority', bs.read_bits, count=1)
    d.add_field('PID', bs.read_bits, count=13)
    d.add_field('transport_scrambling_control', bs.read_bits, count=2)
    d.add_field('adaptation_field_control', bs.read_bits, count=2)
    d.add_field('continuity_counter', bs.read_bits, count=4)
    if d.PID == 0:
        d.add_table(program_association_section)
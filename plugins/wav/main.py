from table import Table
from bitstream import BitStream

def header(t:Table, bs:BitStream):
    bs.bigendien = False
    t.add_field('ChunkID', bs.read_bytes_to_str, count=4)
    t.add_field('ChunkSize', bs.read_bytes, count=4)
    t.add_field('Format', bs.read_bytes_to_str, count=4)
    t.add_field('Subchunk1ID', bs.read_bytes_to_str, count=4)
    t.add_field('Subchunk1Size', bs.read_bytes, count=4)
    t.add_field('AudioFormat', bs.read_bytes, count=2)
    t.add_field('NumChannels', bs.read_bytes, count=2)
    t.add_field('SampleRate', bs.read_bytes, count=4)
    t.add_field('ByteRate', bs.read_bytes, count=4)
    t.add_field('BlockAlign', bs.read_bytes, count=2)
    t.add_field('BitsPerSample', bs.read_bytes, count=2)
    t.add_field('Subchunk2ID', bs.read_bytes_to_str, count=4)
    t.add_field('Subchunk2Size', bs.read_bytes, count=4)

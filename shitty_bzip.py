"""Bzip2-inspired compression and decompression.

Uses some, but not all, of bzip2's "stack":
  - Burrows-Wheeler transform
  - Move-to-front transform
  - Run-length encoding, but a simpler implementation based on PCX
  - Huffman coding
"""
from bitstring import Bits, BitArray, ConstBitStream, ReadError
from huffman import huffman_encode, huffman_decode


def burrows_wheeler_transform(in_bytes):
    string = in_bytes
    rotations = []
    for _ in range(len(in_bytes)):
        string = string[1:] + string[:1]
        rotations.append(string)
    rotations.sort()
    out_bytes = bytearray()
    for s in rotations:
        out_bytes.append(s[-1])
    return bytes(out_bytes), rotations.index(in_bytes)


# Not used, as the naive implementation is too slow even for my test data
def burrows_wheeler_reverse_transform_naive(in_bytes, orig_index):
    rotations = [bytearray() for _ in range(len(in_bytes))]
    for _ in range(len(in_bytes)):
        for i in range(len(rotations)):
            rotations[i].insert(0, in_bytes[i])
        rotations.sort()
    out_bytes = bytes(rotations[orig_index])
    return out_bytes


def burrows_wheeler_reverse_transform(in_bytes, orig_index):
    indexes = [[] for _ in range(256)]
    for i in range(len(in_bytes)):
        c = in_bytes[i]
        indexes[c].append(i)
    flat_indexes = [i for L in indexes for i in L]

    out_bytes = bytearray()
    i = flat_indexes[orig_index]
    while len(out_bytes) < len(in_bytes):
        out_bytes.append(in_bytes[i])
        i = flat_indexes[i]

    return bytes(out_bytes)


def move_to_front_transform(in_bytes):
    symbols = [i for i in range(256)]
    out = bytearray()
    for c in in_bytes:
        i = symbols.index(c)
        del symbols[i]
        symbols.insert(0, c)
        out.append(i)
    return bytes(out)


def move_to_front_reverse_transform(in_bytes):
    symbols = [i for i in range(256)]
    out = bytearray()
    for i in in_bytes:
        c = symbols[i]
        symbols.remove(c)
        symbols.insert(0, c)
        out.append(c)  
    return bytes(out)


MAX_RUN_LENGTH = 127

def run_length_encode(in_bytes):
    in_data = bytearray(in_bytes)
    out_data = bytearray()
    curr_ch = in_data.pop(0)
    run_length = 1
    while len(in_data) > 0:
        ch = in_data.pop(0)
        if ch == curr_ch and run_length < MAX_RUN_LENGTH:
            run_length += 1
        else:
            if run_length == 1 and curr_ch < 128:  # First bit not 1
                out_data.append(curr_ch)
            else:
                out_data.append(run_length | 0b10000000)
                out_data.append(curr_ch)
            curr_ch = ch
            run_length = 1
    # TODO: rewrite the loop so i don't have to do this
    if run_length == 1 and curr_ch < 128:  # First bit not 1
        out_data.append(curr_ch)
    else:
        out_data.append(run_length | 0b10000000)
        out_data.append(curr_ch)
    return bytes(out_data)


def run_length_decode(in_bytes):
    in_data = bytearray(in_bytes)
    out_data = bytearray()
    while len(in_data) > 0:
        ch = in_data.pop(0)
        if ch < 128:
            out_data.append(ch)
        elif len(in_data) > 0:
            run_length = ch & 0b01111111
            ch = in_data.pop(0)
            for _ in range(run_length):
                out_data.append(ch)
    return bytes(out_data)


BLOCK_SIZE_BITS = 16

def encode_block(in_bytes):
    if len(in_bytes) == 1:
        block = BitArray()
        block.append(Bits('0b1'))
        block.append(in_bytes)
        return block.tobytes()

    bw_xf, eof_idx = burrows_wheeler_transform(in_bytes)
    front_xf = move_to_front_transform(bw_xf)
    rle_data = run_length_encode(front_xf)
    huff_data, huff_symbols, serialized_tree = huffman_encode(rle_data, symbol_bits=8)
    huff_len = len(huff_data)
    tree_len = len(serialized_tree)

    block = BitArray()
    block.append(Bits('0b0'))
    block.append(Bits(uint=tree_len, length=16))
    block.append(Bits(serialized_tree))
    block.append(Bits(uint=huff_symbols, length=16))
    block.append(Bits(uint=huff_len, length=16))
    block.append(Bits(huff_data))
    block.append(Bits(uint=eof_idx, length=BLOCK_SIZE_BITS))

    return block.tobytes()


def decode_block(in_bytes):
    in_data = ConstBitStream(in_bytes)
    is_literal_byte = in_data.read('bool')
    if is_literal_byte:
        return in_data.read('bytes:1')

    tree_len = in_data.read('uint:16')
    serialized_tree = in_data.read(f'bytes:{tree_len}')
    huff_symbols = in_data.read('uint:16')
    huff_len = in_data.read('uint:16')
    huff_data = in_data.read(f'bytes:{huff_len}')
    eof_idx = in_data.read(f'uint:{BLOCK_SIZE_BITS}')

    rle_data = huffman_decode(huff_data, huff_symbols, serialized_tree, symbol_bits=8)
    front_xf = run_length_decode(rle_data)
    bw_xf = move_to_front_reverse_transform(front_xf)
    out_bytes = burrows_wheeler_reverse_transform(bw_xf, eof_idx)

    return out_bytes


def bzip0_encode(in_bytes):
    in_data = ConstBitStream(in_bytes)
    out_data = BitArray()
    while in_data.bitpos < in_data.length:
        block_size = min((in_data.length - in_data.bitpos) // 8, 2**BLOCK_SIZE_BITS - 1)
        block_data = in_data.read(f'bytes:{block_size}')
        encoded_block = encode_block(block_data)
        encoded_block_size = len(encoded_block)
        out_data.append(Bits(uint=encoded_block_size, length=BLOCK_SIZE_BITS))
        out_data.append(encoded_block)
    return out_data.tobytes()


def bzip0_decode(in_bytes):
    in_data = ConstBitStream(in_bytes)
    out_data = BitArray()
    try:
        while True:
            encoded_block_size = in_data.read(f'uint:{BLOCK_SIZE_BITS}')
            encoded_block = in_data.read(f'bytes:{encoded_block_size}')
            decoded_block = decode_block(encoded_block)
            out_data.append(decoded_block)
    except ReadError:
        pass
    return out_data.tobytes()


if __name__ == '__main__':
    with open('test.dat', 'rb') as f:
        input_data = f.read()

    print('Encoding...')
    enc = bzip0_encode(input_data)

    print('Decoding...')
    dec = bzip0_decode(enc)

    assert input_data == dec
    print(f'Original size: {len(input_data)}')
    print(f'Compressed size: {len(enc)}')
    print(f'Compression ratio: {len(enc) / len(input_data)}')

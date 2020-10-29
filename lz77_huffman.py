"""Huffman-coded LZ77 encoding and decoding.

Uses one Huffman table for all of the LZ77 symbols, which is not what
DEFLATE does.
"""

from bitstring import Bits, BitArray, ConstBitStream, ReadError
from huffman import huffman_encode, huffman_decode
from lz77 import lz77_encode_to_tokens, lz77_decode_from_tokens, DEFAULT_WINDOW_BITS


def lz77huff_encode(input_data, window_bits=DEFAULT_WINDOW_BITS):
    tokens = lz77_encode_to_tokens(input_data, window_bits)
    symbols = [s for tok in tokens for s in tok]
    bits = BitArray()
    for s in symbols:
        bits.append(Bits(uint=s, length=window_bits))
    encoded_data, num_symbols, serialized_tree = huffman_encode(bits.tobytes(),
                                                                symbol_bits=window_bits)
    return encoded_data, num_symbols, serialized_tree


def lz77huff_decode(encoded_data, num_symbols, serialized_tree, window_bits=DEFAULT_WINDOW_BITS):
    bytestream = huffman_decode(encoded_data, num_symbols, serialized_tree, symbol_bits=window_bits)
    bits = ConstBitStream(bytestream)
    tokens = []
    try:
        while True:
            t = (bits.read(f'uint:{window_bits}'),
                 bits.read(f'uint:{window_bits}'),
                 bits.read(f'uint:{window_bits}'))
            tokens.append(t)
    except ReadError:
        pass
    return lz77_decode_from_tokens(tokens)


if __name__ == '__main__':
    with open('test.dat', 'rb') as f:
        input_data = f.read()

    print('Encoding...')
    enc, length, serialized_tree = lz77huff_encode(input_data)

    print('Decoding...')
    dec = lz77huff_decode(enc, length, serialized_tree)

    assert input_data == dec
    print(f'Original size: {len(input_data)}')
    print(f'Compressed size: {len(enc) + len(serialized_tree)}')
    print(f'Compression ratio: {(len(enc) + len(serialized_tree)) / len(input_data)}')

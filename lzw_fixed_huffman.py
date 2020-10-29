"""Huffman-coded fixed-width LZW encoding and decoding."""

from bitstring import Bits, BitArray, ConstBitStream, ReadError
from huffman import huffman_encode, huffman_decode
from lzw_fixed import lzwf_encode, lzwf_decode


DEFAULT_SYMBOL_LEN = 12


def lzw_huff_encode(in_bytes, symbol_len=DEFAULT_SYMBOL_LEN):
    lzw_bytes = lzwf_encode(input_data, code_len=symbol_len)
    return huffman_encode(lzw_bytes, symbol_bits=symbol_len)


def lzw_huff_decode(data, num_symbols, serialized_tree, symbol_len=DEFAULT_SYMBOL_LEN):
    lzw_data = huffman_decode(data, num_symbols, serialized_tree, symbol_bits=symbol_len)
    return lzwf_decode(lzw_data, code_len=symbol_len)


if __name__ == '__main__':
    with open('test.dat', 'rb') as f:
        input_data = f.read()

    print('Encoding...')
    enc, length, serialized_tree = lzw_huff_encode(input_data, symbol_len=DEFAULT_SYMBOL_LEN)

    print('Decoding...')
    dec = lzw_huff_decode(enc, length, serialized_tree, symbol_len=DEFAULT_SYMBOL_LEN)

    assert input_data == dec
    print(f'Original size: {len(input_data)}')
    print(f'Compressed size: {len(enc) + len(serialized_tree)}')
    print(f'Compression ratio: {(len(enc) + len(serialized_tree)) / len(input_data)}')

"""Huffman coding in Python."""

from functools import total_ordering
from heapq import heapify, heappop, heappush
from bitstring import Bits, BitArray, ConstBitStream, ReadError


@total_ordering
class Symbol:
    def __init__(self, symbol, count=1, left=None, right=None):
        self.symbol = symbol
        self.count = count
        self.left = left
        self.right = right
    def __lt__(self, other):
        return self.count < other.count


def count_symbols(seq):
    symbols = {}
    for s in seq:
        if s in symbols:
            symbols[s].count += 1
        else:
            symbols[s] = Symbol(s)
    return [v for v in symbols.values()]


def make_huffman_tree(symbols):
    pq = symbols.copy()
    heapify(pq)
    while len(pq) > 1:
        s1 = heappop(pq)
        s2 = heappop(pq)
        new = Symbol(None, count=(s1.count + s2.count), left=s1, right=s2)
        heappush(pq, new)
    return pq[0]


def make_encoding_dictionary(tree):
    def encode_node(node, code):
        if node.left is None and node.right is None:
            return {node.symbol: code}
        else:
            merged = {}
            merged.update(encode_node(node.left, code + '0'))
            merged.update(encode_node(node.right, code + '1'))
            return merged
    enc_dict = encode_node(tree, '')
    min_len = min([len(c) for c in enc_dict.values()])
    return enc_dict, min_len


def make_decoding_dictionary(tree):
    d, L = make_encoding_dictionary(tree)
    return {v: k for k, v in d.items()}, L


def serialize_huffman_tree(node, symbol_bits, bit_array=None):
    out = BitArray() if bit_array is None else bit_array
    if node.left is None and node.right is None:
        out.append(Bits(bin='0b1'))
        out.append(Bits(uint=node.symbol, length=symbol_bits))
        return bit_array.tobytes()
    else:
        out.append(Bits(bin='0b0'))
        serialize_huffman_tree(node.left, symbol_bits, bit_array=out)
        serialize_huffman_tree(node.right, symbol_bits, bit_array=out)
        return out.tobytes()


def deserialize_huffman_tree(serialized, symbol_bits):
    bits = serialized if isinstance(serialized, ConstBitStream) else ConstBitStream(serialized)
    is_leaf = bits.read('bool')
    if is_leaf:
        symbol = bits.read(f'uint:{symbol_bits}')
        return Symbol(symbol)
    else:
        left = deserialize_huffman_tree(bits, symbol_bits)
        right = deserialize_huffman_tree(bits, symbol_bits)
        return Symbol(None, left=left, right=right)


def huffman_encode(data, symbol_bits=8):
    bits = ConstBitStream(data)
    symbols = []
    try:
        while True:
            s = bits.read(f'uint:{symbol_bits}')
            symbols.append(s)
    except ReadError:
        pass

    counted_symbols = count_symbols(symbols)
    tree = make_huffman_tree(counted_symbols)
    dictionary, _ = make_encoding_dictionary(tree)

    out = BitArray()
    for s in symbols:
        code = dictionary[s]
        out.append(Bits(f'0b{code}'))
    
    serialized_tree = serialize_huffman_tree(tree, symbol_bits)

    return out.tobytes(), len(data), serialized_tree


def huffman_decode(data, decoded_len, serialized_tree, symbol_bits=8):
    tree = deserialize_huffman_tree(serialized_tree, symbol_bits)
    dictionary, min_code_len = make_decoding_dictionary(tree)

    bits = ConstBitStream(data)
    out = BitArray()
    symbols_decoded = 0
    try:
        while symbols_decoded < decoded_len:
            num_bits = min_code_len
            code = bits.peek(f'bin:{num_bits}')
            while code not in dictionary:
                num_bits += 1
                code = bits.peek(f'bin:{num_bits}')
            out.append(Bits(uint=dictionary[code], length=symbol_bits))
            symbols_decoded += 1
            bits.read(f'bin:{num_bits}')
    except ReadError:
        pass
    return out.tobytes()


if __name__ == '__main__':
    # input_data = b'A MAN A PLAN A CANAL PANAMA'
    with open('test.dat', 'rb') as f:
        input_data = f.read()

    print('Encoding...')
    enc, length, serialized_tree = huffman_encode(input_data)

    print('Decoding...')
    dec = huffman_decode(enc, length, serialized_tree)

    assert input_data == dec
    print(f'Original size: {len(input_data)}')
    print(f'Compressed size: {len(enc) + len(serialized_tree)}')
    print(f'Compression ratio: {(len(enc) + len(serialized_tree)) / len(input_data)}')

    pass

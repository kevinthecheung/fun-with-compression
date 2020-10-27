"""LZSS (LZ77 variant) encoding and decoding."""

from bitstring import Bits, BitArray, ConstBitStream, ReadError
from lz77 import lz77_encode_to_tokens, lz77_decode_from_tokens, DEFAULT_WINDOW_BITS, REFERENCE_SIZE_BITS


LITERAL = 0
REFERENCE = 1


def lzss_encode(input_data, window_bits=DEFAULT_WINDOW_BITS):
    tokens = lz77_encode_to_tokens(input_data, window_bits)
    out = BitArray()
    for t in tokens:
        if t[0] == 0 or t[1] == 0:
            out.append(Bits(uint=LITERAL, length=1))
            out.append(Bits(uint=t[2], length=8))
        else:
            out.append(Bits(uint=REFERENCE, length=1))
            out.append(Bits(uint=t[0], length=window_bits))
            out.append(Bits(uint=t[1], length=REFERENCE_SIZE_BITS))
            out.append(Bits(uint=t[2], length=8))
    return out.tobytes()


def lzss_decode(encoded_data, window_bits=DEFAULT_WINDOW_BITS):
    encoded = ConstBitStream(encoded_data)
    tokens = []
    try:
        while True:
            if encoded.read('uint:1') == LITERAL:
                tokens.append((0, 0, encoded.read('uint:8')))
            else:
                pfx_dist = encoded.read(f'uint:{window_bits}')
                pfx_len = encoded.read(f'uint:{REFERENCE_SIZE_BITS}')
                next_ch = encoded.read('uint:8')
                tokens.append((pfx_dist, pfx_len, next_ch))
    except ReadError:
        pass
    return lz77_decode_from_tokens(tokens)


if __name__ == '__main__':
    with open('test.dat', 'rb') as f:
        input_data = f.read()

    window_bits = 12

    print('Encoding...')
    enc = lzss_encode(input_data, window_bits=window_bits)

    print('Decoding...')
    dec = lzss_decode(enc, window_bits=window_bits)

    print(f'Decoded data matches original: {input_data == dec}')
    print(f'Original size: {len(input_data)}')
    print(f'Compressed size: {len(enc)}')
    print(f'Compression ratio: {len(enc) / len(input_data)}')

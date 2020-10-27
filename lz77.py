"""LZ77 encoding and decoding."""

from bitstring import Bits, BitArray, ConstBitStream, ReadError


DEFAULT_WINDOW_BITS = 12  # 4K window
REFERENCE_SIZE_BITS = 4   # 16 character max


def get_longest_prefix(input_data, input_idx, window, max_window_len):
    win_start = window[0]
    win_end = window[1]
    prefix_dist = 0
    prefix_len = 0
    next_ch = input_data[input_idx]
    max_prefix_len = min(2**REFERENCE_SIZE_BITS - 1, len(input_data) - input_idx)
    for candidate_pfx_len in range(2, max_prefix_len):
        candidate_pfx = input_data[input_idx:input_idx+candidate_pfx_len]
        idx = input_data.find(candidate_pfx, win_start)
        if win_start <= idx and idx < win_end:
            prefix_dist = input_idx - idx
            prefix_len = candidate_pfx_len
            next_ch = input_data[input_idx + candidate_pfx_len]
    return prefix_dist, prefix_len, next_ch


def lz77_encode_to_tokens(input_data, window_bits):
    max_window_len = 2**window_bits - 1
    output = []
    input_idx = 0
    while input_idx < len(input_data):
        win_start = max(0, input_idx - max_window_len)
        prefix_dist, prefix_len, next_ch = get_longest_prefix(
                input_data, input_idx, (win_start, input_idx), max_window_len)
        output.append((prefix_dist, prefix_len, next_ch))
        input_idx += prefix_len + 1
    return output


def lz77_encode(input_data, window_bits=DEFAULT_WINDOW_BITS):
    tokens = lz77_encode_to_tokens(input_data, window_bits)
    out = BitArray()
    for t in tokens:
        out.append(Bits(uint=t[0], length=window_bits))
        out.append(Bits(uint=t[1], length=REFERENCE_SIZE_BITS))
        out.append(Bits(uint=t[2], length=8))
    return out.tobytes()


def lz77_decode_from_tokens(tokens):
    decoded = bytearray()
    cur_idx = 0
    for t in tokens:
        pfx_dist = t[0]
        pfx_len = t[1]
        next_ch = t[2]
        pfx_idx = cur_idx - pfx_dist
        for i in range(pfx_idx, pfx_idx + pfx_len):
            decoded.append(decoded[i])
        decoded.append(next_ch)
        cur_idx += pfx_len + 1
    return bytes(decoded)


def lz77_decode(encoded_data, window_bits=DEFAULT_WINDOW_BITS):
    encoded = ConstBitStream(encoded_data)
    tokens = []
    try:
        while True:
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
    enc = lz77_encode(input_data, window_bits=window_bits)

    print('Decoding...')
    dec = lz77_decode(enc, window_bits=window_bits)

    print(f'Decoded data matches original: {input_data == dec}')
    print(f'Original size: {len(input_data)}')
    print(f'Compressed size: {len(enc)}')
    print(f'Compression ratio: {len(enc) / len(input_data)}')

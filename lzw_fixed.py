"""Fixed-width LZW encoding and decoding."""

from bitstring import Bits, BitArray, ConstBitStream, ReadError


DEFAULT_CODE_LEN = 12


def lzwf_encode(in_bytes, code_len=DEFAULT_CODE_LEN):
    max_entries = 2**code_len
    in_array = bytearray(in_bytes)
    dictionary = {bytes([i]): i for i in range(256)}
    out_array = BitArray()
    while len(in_array) > 1:
        # Find string s that's not in the dictionary
        s = b''
        while (s in dictionary or s == b'') and len(in_array) > 0:
            s = s + bytes([in_array.pop(0)])
        in_array.insert(0, s[-1])

        # Emit code for the s[:-1], which is in the dictionary
        out_array.append(Bits(uint=dictionary[s[:-1]], length=code_len))

        # If there's room in the dictionary, add s
        if len(dictionary) < max_entries:
            dictionary[s] = len(dictionary)
    # Emit code for final value
    out_array.append(Bits(uint=dictionary[bytes([in_array.pop(0)])], length=code_len))
    return out_array.tobytes()


def lzwf_decode(in_array, code_len=DEFAULT_CODE_LEN):
    max_entries = 2**code_len
    in_stream = ConstBitStream(in_array)
    dictionary = {i: bytes([i]) for i in range(256)}
    out_array = bytes()
    while True:
        try:
            # Read a code
            k = in_stream.read(f'uint:{code_len}')

            # Look up code and emit value
            v = dictionary[k]
            out_array = out_array + v

            # Add v + v_next[0] to dictionary
            c = len(dictionary)
            if c < max_entries:
                k_next = in_stream.peek(f'uint:{code_len}')
                if k_next < c:
                    v_next = dictionary[k_next]
                    dictionary[c] = v + v_next[:1]
                else:
                    dictionary[c] = v + v[:1]
        except ReadError:
            break
    return bytes(out_array)


if __name__ == '__main__':
    with open('test.dat', 'rb') as f:
        orig = f.read()

    print('Encoding...')
    enc = lzwf_encode(orig)

    print('Decoding...')
    dec = lzwf_decode(enc)

    print(f'Decoded data matches original: {orig == dec}')
    print(f'Original size: {len(orig)}')
    print(f'Compressed size: {len(enc)}')
    print(f'Compression ratio: {len(enc) / len(orig)}')

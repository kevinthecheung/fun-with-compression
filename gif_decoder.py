"""A very slow GIF decoder."""

from bitstring import Bits, BitArray, ConstBitStream, ReadError

CLEAR_CODE = -1
END_CODE = -2

MAX_CODE_LEN = 12
MAX_DICT_ENTRIES = 2**MAX_CODE_LEN


def decode_lzw(raster_data):
    dictionary = init_dictionary(2**raster_data['code_size'])
    code_len = raster_data['code_size'] + 1
    encoded = GifDataStream(raster_data['encoded_data'])
    decoded = bytes()
    while True:
        try:
            # Read a code
            k = encoded.read_uint(code_len)

            # Look up code and emit value
            v = dictionary[k]
            if v == CLEAR_CODE:
                dictionary = init_dictionary(2**raster_data['code_size'])
                code_len = raster_data['code_size'] + 1
                continue
            if v == END_CODE:
                break
            decoded = decoded + v

            # Add v + v_next[0] to dictionary
            c = len(dictionary)
            if c < MAX_DICT_ENTRIES:
                if c == 2**code_len:
                    code_len = min(MAX_CODE_LEN, code_len + 1)
                k_next = encoded.peek_uint(code_len)
                if k_next < c:
                    v_next = dictionary[k_next]
                    if isinstance(v_next, bytes):
                        dictionary[c] = v + v_next[:1]
                else:
                    dictionary[c] = v + v[:1]
        except ReadError:
            break
    return decoded


def init_dictionary(n):
    dictionary = {i: bytes([i]) for i in range(n)}
    dictionary[n] = CLEAR_CODE
    dictionary[n + 1] = END_CODE
    return dictionary


class GifDataStream:
    def __init__(self, bytez):
        self.bytez = bytearray(bytez)
        self.remainder = BitArray()

    def read_uint(self, n):
        while len(self.remainder) < n:
            self.remainder.prepend(Bits(bytearray([self.bytez.pop(0)])))
        uint = self.remainder.uint & (2**n - 1)
        self.remainder >>= n
        del self.remainder[0:n]
        return uint

    def peek_uint(self, n):
        s = self.remainder.copy()
        i = 0
        while len(s) < n:
            s.prepend(Bits(bytearray(self.bytez[i:i+1])))
            i += 1
        bits = Bits(s)
        return bits.uint & (2**n - 1)

###############################################################################

def read_signature(stream):
    sig = stream.read('bytes:3')
    ver = stream.read('bytes:3')
    return sig, ver


def read_screen_descriptor(stream):
    screen = {}
    screen['width'] = stream.read('uintle:16')
    screen['height'] = stream.read('uintle:16')
    screen['has_palette'] = stream.read('bool')
    screen['bits_per_channel'] = stream.read('uint:3') + 1
    stream.read('pad:1')
    screen['bits_per_pixel'] = stream.read('uint:3') + 1
    screen['background_color'] = stream.read('uint:8')
    stream.read('pad:8')
    return screen


def read_palette(stream, bpp):
    return bytearray(stream.read('bytes:{}'.format(3 * 2**bpp)))


def read_image_descriptor(stream):
    sentinel = stream.read('bytes:1')
    if sentinel != b',':
        raise ValueError
    image = {}
    image['left'] = stream.read('uintle:16')
    image['top'] = stream.read('uintle:16')
    image['width'] = stream.read('uintle:16')
    image['height'] = stream.read('uintle:16')
    image['has_palette'] = stream.read('bool')
    image['is_interlaced'] = stream.read('bool')
    stream.read('pad:3')
    image['bits_per_pixel'] = stream.read('uint:3') + 1
    return image


def read_raster_data(stream):
    data = {}
    data['code_size'] = stream.read('uint:8')
    data['encoded_data'] = b''
    block_size = stream.read('uint:8')
    while block_size > 0:
        data['encoded_data'] += stream.read('bytes:{}'.format(block_size))
        block_size = stream.read('uint:8')
    return data


def skip_extension_block(stream):
    sentinel = stream.read('bytes:1')
    if sentinel != b'!':
        raise ValueError
    func_code = stream.read('uint:8')
    block_size = stream.read('uint:8')
    while block_size > 0:
        stream.read('bytes:{}'.format(block_size))
        block_size = stream.read('uint:8')


def peek_next(stream):
    sentinel = stream.peek('bytes:1')
    if sentinel == b',':
        return 'IMAGE_DESCRIPTOR'
    elif sentinel == b'!':
        return 'EXTENSION_BLOCK'
    elif sentinel == b';':
        return 'TERMINATOR'
    else:
        return 'UNKNOWN'

################################################################################

def decode_gif(filename):
    """Decode a GIF into a flat buffer."""
    with open(filename, 'rb') as f:
        bitstream = ConstBitStream(f.read())

    signature, version = read_signature(bitstream)
    if signature != b'GIF':
        raise ValueError

    screen = read_screen_descriptor(bitstream)
    buffer = bytearray()

    if screen['has_palette']:
        palette = read_palette(bitstream, screen['bits_per_pixel'])

    block_type = peek_next(bitstream)
    while block_type != 'TERMINATOR':
        if block_type == 'IMAGE_DESCRIPTOR':
            image_info = read_image_descriptor(bitstream)
            if image_info['has_palette']:
                # We'll just use the local palette if it's present
                palette = read_palette(bitstream, image_info['bits_per_pixel'])
            raster_data = read_raster_data(bitstream)
            buffer += bytearray(decode_lzw(raster_data))
        elif block_type == 'EXTENSION_BLOCK':
            skip_extension_block(bitstream)
        else:
            raise ValueError
        block_type = peek_next(bitstream)
    return screen, palette, buffer

################################################################################

if __name__ == '__main__':
    # Decode GIF into a PIL image, for testing
    from PIL import Image

    screen, palette, buffer = decode_gif('macallan.gif')
    image = Image.frombytes('P', 
                            (screen['width'], screen['height']),
                            bytes(buffer))
    image.putpalette(palette)
    image.show()

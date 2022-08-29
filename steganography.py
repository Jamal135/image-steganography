''' Creation Date: 27/08/2022 '''


from PIL import Image
from functools import reduce
from itertools import product
from secrets import token_hex
from random import seed, sample, randint


def decimal_encoding(text: str):
    ''' Returns: Text converted to base10 integer. '''
    try:
        return int(reduce(lambda a, b: a * 256 + b, map(ord, text), 0))
    except Exception as e:
        raise ValueError(f'Failed to encode: {text}') from e


def load_image(filename: str, type: str = '.png'):
    ''' Returns: Image object and Enum of WIDTH and HEIGHT. '''
    if not filename.endswith(type): # Only support PNG
        filename += type
    try:
        image = Image.open(f'Images/{filename}')
    except Exception as e:
        raise ValueError(f'No .PNG at Images/{filename}') from e
    size = image.size
    class Size():
        WIDTH = size[0]
        HEIGHT = size[1]
        PIXELS = size[0] * size[1]
    return image, Size


def shuffle(key: int, data):
    ''' Returns: Data shuffled with key as seed. '''
    seed(key)
    return sample(data, len(data))


def generate_context(key: int, Image: Image, Size: object, key_pixels: int = 16):
    ''' Returns: List of tuple coordinates in image and image specific key. '''
    key = decimal_encoding(key)
    key *= (Size.PIXELS * 99) # Adjust key by image size
    coords = shuffle(key, [*product(range(Size.WIDTH), range(Size.HEIGHT))])
    pixels = [Image.getpixel((coords[point][0], coords[point][1]))
              for point in range(key_pixels - 1)]
    key *= (sum(map(sum, pixels))) # Adjust key by key pixels
    coords = shuffle(key, coords[key_pixels:])
    return coords, key


def generate_header(Configuration: object):
    ''' Returns: Built binary header data specifying settings. '''
    colours = list(Configuration.COLOURS.values())
    indexs = list(Configuration.INDEXS.values())
    method = Configuration.METHOD
    method_bool = "1" if method == "random" else "0"
    colour_table = ["0", "0", "0"]
    for colour in colours:
        colour_table[colour] = "1"
    index_table = ["0", "0", "0", "0", "0", "0", "0", "0"]
    for index in indexs:
        index_table[index] = "1"
    return method_bool + "".join(colour_table) + "".join(index_table)


def random_sample(key: int, options: list, length: int, number_picked: int = 1):
    ''' Returns: Variable length list of lists of selected options. '''
    seed(key)
    return [sample(options, k = number_picked) for _ in range(length)]


def integer_conversion(data: int, method: str):
    ''' Returns: Number converted to or from binary. '''
    if method == 'binary':
        return bin(data).replace('0b', '').zfill(8)
    else:
        return int(data, 2)


def attach_header(Image: Image, key: int, header: str, coords: list):
    ''' Returns: Modified image with header data attached for extraction. '''
    length = len(header) # Stored as random method any colour, smallest index
    header_coords = coords[:length - 1]
    colours = random_sample(key, [0,1,2], length)
    colours = [item for sublist in colours for item in sublist]
    for i, position in enumerate(header_coords):
        pixel = list(Image.getpixel((position[0], position[1])))
        value = integer_conversion(pixel[colours[i]], 'binary')
        modified_value = integer_conversion(value[:-1] + header[i], 'integer')
        pixel[colours[i]] = modified_value 
        Image.putpixel((coords[i][0], coords[i][1]), tuple(pixel))
    return coords[length:], Image    


def build_object(key: int, method: str, noise: bool, colours: list, indexs: list):
    ''' Returns: Configuration object of steganographic storage settings. '''
    if colours is None:
        colours = [0, 1, 2]
    if indexs is None:
        indexs = [6, 7]
    colour_list = ['red', 'green', 'blue']
    index_list = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th']
    class Configuration:
        COLOURS = {colour_list[i]: i for i in colours}
        INDEXS = {index_list[i]: i for i in indexs}
        VOLUME = len(colours) * len(indexs) if method == 'all' else len(indexs)
        METHOD = method
        NOISE = noise
        KEY = key
    return Configuration


def binary_conversion(data: str, method: str):
    ''' Returns: Data converted to or from binary. '''
    if method == 'binary':
        return ''.join([bin(byte)[2:].zfill(8) for byte in bytearray(data, 'utf-8')])
    byte_list = int(data, 2).to_bytes(len(data) // 8, byteorder='big')
    return byte_list.decode('utf-8')


def generate_numbers(min_value: int, max_value: int, number_values: int):
    ''' Returns: Variable length string of random numbers in range. '''
    seed(token_hex(64))
    return "".join([str(randint(min_value, max_value)) for _ in range(number_values)])


def generate_message(Configuration: object, data: str, coords: list):
    ''' Returns: '''
    capacity = len(coords)
    data = binary_conversion(data, 'binary')
    end_key_size = len(integer_conversion(capacity, 'binary'))
    data_size = len(data)
    size = end_key_size + data_size
    if size > capacity: # Test if message can fit inside the image
        raise ValueError(f"Message size exceeded by {size - capacity} bits")
    noise = generate_numbers(0, 1, capacity - size) if Configuration.NOISE else ''
    end_key = integer_conversion(data_size, 'binary').zfill(end_key_size)
    return end_key + data + noise # Binary, end key specifies index of data end


def generate_coords(Configuration: object, Size: object, pixel_coords: list):
    ''' Returns: Shuffled data location tuples (Width, Height, Colour, Index). '''
    colours = list(Configuration.COLOURS.values())
    indexs = list(Configuration.INDEXS.values())
    method = Configuration.METHOD
    key = Configuration.KEY
    length = Size.PIXELS
    if method == 'random': # If random need to pick random colour option per pixel
        colours = random_sample(key, colours, length)
    data_coords = []
    for i, coordinate in enumerate(pixel_coords):
        for colour in colours[i] if method == 'random' else colours:
            data_coords.extend((coordinate[0], coordinate[1], colour, index) 
                               for index in indexs)
    return shuffle(key, data_coords)


def attach_data(Image: Image, Configuration: object, binary_message: str, coords: list):
    ''' Returns: Image with all required pixels steganographically modified. '''
    if not Configuration.NOISE: # Optimise if not modifying every pixel
        coords = coords[:len(binary_message)]
    for i, position in enumerate(coords):
        pixel = list(Image.getpixel((position[0], position[1])))
        value = list(integer_conversion(pixel[position[2]], 'binary'))
        value[position[3]] = binary_message[i]
        modified_value = integer_conversion(''.join(value), 'integer')
        pixel[position[2]] = modified_value
        Image.putpixel((coords[i][0], coords[i][1]), tuple(pixel))
    return Image


def save_image(filename: str, Image: Image, type: str = '.png'):
    ''' Returns: Saved image at location output. '''
    filename = f'{filename[:-4]}_result{type}' if filename.endswith(type) \
                else f'{filename}_result{type}'
    Image.save(f'Images/{filename}')


def extract_header(Image: Image, key: int, coords: list):
    ''' Returns: Header data extracted and unpacked. '''
    pass


def extract_message():
    pass


def data_insert(filename: str, key: str, data: str, method: str = 'random', 
                colours: list = None, indexs: list = None, noise: bool = False):
    ''' Returns: Selected image with secret data steganographically attached. '''
    Image, Size = load_image(filename)
    coords, image_key = generate_context(key, Image, Size)
    Configuration = build_object(image_key, method, noise, colours, indexs)
    header = generate_header(Configuration) # Specifies Configuration for extract
    cut_coords, Image = attach_header(Image, image_key, header, coords)
    data_coords = generate_coords(Configuration, Size, cut_coords)
    binary_message = generate_message(Configuration, data, data_coords)
    Image = attach_data(Image, Configuration, binary_message, data_coords)
    save_image(filename, Image)


def data_extract(filename: str, key: str):
    ''' Returns: Data steganographically extracted from selected image. '''
    Image, Size = load_image(filename)
    coords, image_key = generate_context(key, Image, Size)
    method, noise, colours, indexs, cut_coords = extract_header(Image, key, coords)
    Configuration = build_object(image_key, method, noise, colours, indexs)
    data_coords = generate_coords(Configuration, Size, cut_coords)
    binary_message = extract_message()
    
# Bug where with multiple indexs per pixel only most recent is saved
data_insert('gate', "I like pineapples with toast", "hello world", method = 'all', indexs = [6,7], colours=[1])

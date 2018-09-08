import numpy
from PIL import Image, ImageEnhance
import struct
from io import BytesIO
import time
from shutil import copyfileobj
import bitstruct
import sys
import os
import math
import argparse
import subprocess
import traceback
import _io

sz_present = True
br_present = True
zst_present = True
# compressors
import lzma
import bz2
try: import snappy
except: sz_present = False
try: import brotli
except: br_present = False
try: import zstd
except: zst_present = False

Image.MAX_IMAGE_PIXELS = None
version = '0.9.9'
release = 1

def relative_path(relative_path):
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.realpath(__file__))

    return os.path.join(base_path, relative_path)

def human_size(filesize):
    filesize = abs(filesize)
    p = int(math.floor(math.log(filesize, 2)/10))
    return "%0.2f %s" % (filesize/math.pow(1024,p), ['Bytes','KB','MB','GB','TB','PB','EB','ZB','YB'][p])

class MAPFException(Exception):
    pass

m0_quality = [(0, 0), (1, 0), (2, 0), (0, 1), (3, 0), (4, 0), (1, 1), (5, 0), (2, 1), (6, 0), (7, 0), (3, 1), (4, 1), (0, 2), (5, 1), (6, 1), (7, 1), (1, 2), (2, 2), (3, 2), (4, 2), (0, 3), (5, 2), (6, 2), (7, 2), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3)]
m1_quality = [(0, 0), (1, 0), (2, 0), (0, 1), (3, 0), (4, 0), (1, 1), (5, 0), (2, 1), (6, 0), (3, 1), (7, 0), (4, 1), (0, 2), (5, 1), (6, 1), (1, 2), (7, 1), (2, 2), (3, 2), (0, 3), (4, 2), (5, 2), (1, 3), (6, 2), (2, 3), (7, 2), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3)]
m3_quality = [(0, 0), (0, 1), (1, 0), (2, 0), (0, 2), (0, 3), (0, 4), (0, 5), (1, 1), (0, 6), (3, 0), (2, 1), (1, 2), (0, 7), (4, 0), (1, 3), (0, 8), (1, 4), (0, 9), (0, 10), (1, 5), (0, 11), (1, 6), (3, 1), (0, 12), (2, 2), (0, 13), (2, 3), (2, 4), (2, 5), (0, 14), (5, 0), (2, 6), (0, 15), (6, 0), (3, 2), (3, 3), (7, 0), (3, 4), (1, 7), (1, 8), (1, 9), (4, 1), (3, 5), (1, 10), (1, 11), (3, 6), (1, 12), (1, 13), (2, 7), (2, 8), (2, 9), (2, 10), (2, 11), (1, 14), (4, 2), (1, 15), (2, 12), (4, 3), (4, 4), (5, 1), (2, 13), (4, 5), (3, 7), (3, 8), (3, 9), (4, 6), (2, 14), (3, 10), (3, 11), (6, 1), (2, 15), (7, 1), (3, 12), (5, 2), (3, 13), (5, 3), (5, 4), (3, 14), (6, 2), (5, 5), (6, 3), (7, 2), (5, 6), (4, 7), (3, 15), (6, 4), (4, 8), (7, 3), (4, 9), (7, 4), (4, 10), (6, 5), (4, 11), (6, 6), (7, 5), (4, 12), (7, 6), (4, 13), (5, 7), (5, 8), (4, 14), (5, 9), (5, 10), (4, 15), (5, 11), (6, 7), (6, 8), (6, 9), (7, 7), (7, 8), (5, 12), (6, 10), (7, 9), (6, 11), (7, 10), (5, 13), (7, 11), (6, 12), (5, 14), (7, 12), (6, 13), (5, 15), (7, 13), (6, 14), (7, 14), (6, 15), (7, 15)]
m4_quality = [(0, 0), (1, 0), (2, 0), (0, 1), (3, 0), (4, 0), (1, 1), (2, 1), (5, 0), (6, 0), (7, 0), (3, 1), (4, 1), (0, 2), (5, 1), (6, 1), (7, 1), (1, 2), (2, 2), (3, 2), (4, 2), (0, 3), (5, 2), (6, 2), (7, 2), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3)]
m5_quality = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (0, 1), (7, 0), (1, 1), (0, 2), (2, 1), (3, 1), (4, 1), (5, 1), (1, 2), (2, 2), (6, 1), (3, 2), (7, 1), (4, 2), (5, 2), (6, 2), (0, 3), (7, 2), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3)]
m7_quality = [0, 8, 16, 24, 32, 40, 48, 56, 64, 72, 1, 9, 80, 88, 104, 96, 112, 120, 17, 25, 33, 41, 10, 2, 49, 57, 18, 26, 65, 73, 34, 42, 50, 58, 81, 89, 11, 3, 105, 97, 113, 121, 12, 4, 66, 74, 19, 27, 35, 43, 82, 90, 20, 28, 13, 5, 51, 59, 36, 44, 106, 98, 114, 122, 52, 60, 67, 75, 21, 29, 14, 6, 37, 45, 15, 7, 68, 76, 83, 91, 53, 61, 107, 99, 115, 123, 22, 30, 84, 92, 23, 31, 38, 46, 69, 77, 100, 108, 39, 47, 116, 124, 54, 62, 55, 63, 85, 93, 101, 109, 70, 78, 117, 125, 71, 79, 86, 94, 87, 95, 102, 110, 118, 126, 103, 111, 119, 127]

versions = {0: '0.9.1', 1: '0.9.9'}

compress_modes = {'xz': 0,
                  'lzma': 0,
                  'lz': 0,
                  'bz2': 1,
                  'bzip2': 1,
                  'nz': 2,
                  'nanozip': 2,
                  'nano_zip': 2,
                  'nano-zip': 2,
                  'brotli': 3,
                  'br': 3,
                  'zstd': 4,
                  'zst': 4,
                  'snappy': 5,
                  'sz': 5,
                  'without': 6,
                  'bcm': 7}
_compress_modes_reversed = dict((v,k) for k,v in compress_modes.items())

image_modes = {'RGB': 0,
               'RGBA': 1,
               'LOSSLESS_YUV': 2,
               'LOSSLESS_YCBCR': 2,
               'YUV': 3,
               'YCBCR': 3,
               'L': 4,
               'LUMA': 4,
               'BW': 4,
               'PREVIEW': 5,
               'DRAFT': 5,
               'LOSSLESS_YUVA': 6,
               'LOSSLESS_YCBCRA': 6,
               'BLOCKING_YUV': 7,
               'CHUNKED_YUV': 7,
               'BLOCKING_YCBCR': 7,
               'CHUNKED_YCBCR':7}

available_compressions = {'lzma': True,
                          'bzip2': True,
                          'nanozip': os.path.exists(relative_path('nz.exe')),
                          'brotli': br_present,
                          'zst': zst_present,
                          'snappy': sz_present,
                          'without': True,
                          'bcm': os.path.exists(relative_path('bcm.exe'))}

_image_modes_reversed = dict((v,k) for k,v in image_modes.items())

enlargers = [Image.BICUBIC, Image.BILINEAR, Image.LANCZOS, Image.NEAREST]

errors = ['INVALID IMAGE MODE OR UNSUPPORTED IN THIS VERSION.',
          'FILE DOESN\'T LOOKS LIKE ORIGINAL MAPF FILE.',
          'INVALID DATA LENGTH.',
          'INVALID DATA COMPRESSION MODE.',
          'INPUT FILE NOT FOUND.',
          'QUALITY SCALLAR HAS TO BE IN RANGE 0-3.',
          'QUALITY COLORS HAS TO BE IN RANGE 0-7.',
          'COMPRESS MODE HAS TO BE IN RANGE 0-7. ({})'.format(str(compress_modes)),
          'QUALITY SUBSAMPLING (YUV) HAS TO BE IN RANGE 0-15.',
          'QUALITY HAS TO BE IN RANGE 0-31 IN MODES 0,1,4,5 OR IN RANGE 0-127 IN MODE 3, 7.',
          'BCM EXECUTABLE NOT FOUND, PLEASE SELECT OTHER IMAGE COMPRESSION OR DOWNLOAD IT.',
          'OUTPUT PATH OF MAPF NOT PROVIDED, YOU CAN USE return_data=1 TO RETURN IMAGE AS BYTE-STRING.',
          'IMAGE SIZE TOO SMALL!\nIMAGE DOWNSCALLING FAILED!\nTRY WITH OTHER IMAGE MODE OR HIGHER QUALITY.',
          'NANOZIP EXECUTABLE NOT FOUND, PLEASE SELECT OTHER IMAGE COMPRESSION OR DOWNLOAD IT.']

warns = ['INPUT IMAGE HAS MORE THAN 2073600 PIXELS. COMPRESSING CAN TAKE A MUCH TIME.',
         'YOU\'RE TRYING TO CALL AN EXTERNAL COMPILED BINARY, IN return_data MODE IT NOT WORKS, BECAUSE IT REQUIRE AN EXTERNAL FILE TO COMPRESS IT.',
         'INPUT IMAGE TAKES MORE THAN 300MB OF MEMORY.\nKILL PROCESS IF YOU HAVE LESS THAN {} MB OF FREE MEMORY.']

def save(input_path, output_path=None, image_mode=3, quality_scalar=3, quality_colors=6, quality_subsampling=4, quality=-1, compress_mode=0, compress_power=9, enlarger=2, optimizer_enabled=False, optimizer_chunk=8, optimizer_maxdiff=25, helper=True, compress_helper_max=8, debug=True, quiet=False, return_data=False):

    try: compress_mode = compress_modes[compress_mode.lower()]
    except (KeyError, AttributeError): pass
    try: image_mode = image_modes[image_mode.upper()]
    except (KeyError, AttributeError): pass

    if output_path == None and not return_data:
        if __name__ == '__main__':
            print('MAPF ERROR:', errors[11])
            sys.exit(15)
        else:
            raise MAPFException(errors[11])

    time_old = time.time()
    if debug:
        print('CHECKING INPUTS FOR ERRORS...')
    
    outf = output_path
    imf = input_path
    quality_x = quality_scalar
    quality_y = quality_colors
    quality_z = quality_subsampling
    try:
        compress_mode = int(compress_mode)
    except:
        if __name__ == '__main__':
            print('MAPF ERROR:', errors[7])
            sys.exit(10)
        else:
            raise MAPFException(errors[7])
    if not os.path.exists(imf):
        if __name__ == '__main__':
            print('MAPF ERROR:', errors[4])
            sys.exit(7)
        else:
            raise MAPFException(errors[4])

    if image_mode > 7:
        if __name__ == '__main__':
            print('MAPF ERROR:', errors[0])
            sys.exit(2)
        else:
            raise MAPFException(errors[0])

    if quality == -1:

        if quality_x not in range(4):
            if __name__ == '__main__':
                print('MAPF ERROR:', errors[5])
                sys.exit(8)
            else:
                raise MAPFException(errors[5])

        if quality_y not in range(8):
            if __name__ == '__main__':
                print('MAPF ERROR:', errors[6])
                sys.exit(9)
            else:
                raise MAPFException(errors[9])

        if quality_z not in range(16):
            if __name__ == '__main__':
                print('MAPF ERROR:', errors[8])
                sys.exit(12)
            else:
                raise MAPFException(errors[8])

    else:
        if image_mode == 3 or image_mode == 7:
            if quality not in range(128):
                if __name__ == '__main__':
                    print('MAPF ERROR:', errors[9])
                    sys.exit(13)
                else:
                    raise MAPFException(errors[9])
        else:
            if quality not in range(32):
                if __name__ == '__main__':
                    print('MAPF ERROR:', errors[9])
                    sys.exit(13)
                else:
                    raise MAPFException(errors[9])

        if image_mode == 0:
            quality_y, quality_x = m0_quality[quality]
        if image_mode == 1:
            quality_y, quality_x = m1_quality[quality]
        if image_mode == 3:
            quality_y, quality_z = m3_quality[quality]
        if image_mode == 4:
            quality_y, quality_x = m4_quality[quality]
        if image_mode == 5:
            quality_y, quality_x = m5_quality[quality]

    if compress_mode not in range(8):
        if __name__ == '__main__':
            print('MAPF ERROR:', errors[7])
            sys.exit(10)
        else:
            raise MAPFException(errors[7])

    # FREE 134, 158
    BK_CLR = bytes([128])
    WT_CLR = bytes([129])
    SAME_CLR = bytes([130])
    RD_CLR = bytes([131])
    GR_CLR = bytes([132])
    BL_CLR = bytes([133])
    FS_CLR = bytes([134])
    NEGATIVE_CLR = bytes([135])
    _2BC_SAME = bytes([143])
    _3BC_SAME = bytes([144])
    _4BC_SAME = bytes([145])
    _5BC_SAME = bytes([146])
    _6BC_SAME = bytes([147])
    _7BC_SAME = bytes([148])
    _8BC_SAME = bytes([149])
    p2_BRIGHTNESS = bytes([150])
    m2_BRIGHTNESS = bytes([151])
    p3_BRIGHTNESS = bytes([152])
    m3_BRIGHTNESS = bytes([153])
    p4_BRIGHTNESS = bytes([154])
    m4_BRIGHTNESS = bytes([155])
    p5_BRIGHTNESS = bytes([156])
    m5_BRIGHTNESS = bytes([157])

    p0p0m1_BRIGHTNESS = bytes([136])
    p0m1m1_BRIGHTNESS = bytes([137])
    m1m1m1_BRIGHTNESS = bytes([138])
    m1p0p0_BRIGHTNESS = bytes([139])
    m1m1p0_BRIGHTNESS = bytes([140])
    m1p0m1_BRIGHTNESS = bytes([141])
    p0m1p0_BRIGHTNESS = bytes([142])

    p0p0p1_BRIGHTNESS = bytes([159])
    p0p1p1_BRIGHTNESS = bytes([160])
    p1p1p1_BRIGHTNESS = bytes([161])
    p1p0p0_BRIGHTNESS = bytes([162])
    p1p1p0_BRIGHTNESS = bytes([163])
    p1p0p1_BRIGHTNESS = bytes([164])
    p0p1p0_BRIGHTNESS = bytes([165])

    m1m1p1_BRIGHTNESS = bytes([166])
    m1p0p1_BRIGHTNESS = bytes([167])
    m1p1m1_BRIGHTNESS = bytes([168])
    m1p1p0_BRIGHTNESS = bytes([169])
    m1p1p1_BRIGHTNESS = bytes([170])
    p0m1p1_BRIGHTNESS = bytes([171])
    p0p1m1_BRIGHTNESS = bytes([172])
    p1m1m1_BRIGHTNESS = bytes([173])
    p1m1p0_BRIGHTNESS = bytes([174])
    p1m1p1_BRIGHTNESS = bytes([175])
    p1p0m1_BRIGHTNESS = bytes([176])
    p1p1m1_BRIGHTNESS = bytes([177])

    def create_img(img, dividor):
        return numpy.array(img)//dividor

    def cutsize(img, divide):
        return img.resize((round(img.size[0]/divide), round(img.size[1]/divide)), enlargers[enlarger])

    def make(pixels):
        red = numpy.linspace(start=pixels[0::3][0], stop=pixels[0::3][-1], num=len(pixels[0::3]))
        green = numpy.linspace(start=pixels[1::3][0], stop=pixels[1::3][-1], num=len(pixels[1::3]))
        blue = numpy.linspace(start=pixels[2::3][0], stop=pixels[2::3][-1], num=len(pixels[2::3]))
        return numpy.around(numpy.ravel(numpy.column_stack((red,green,blue)))).astype(numpy.uint8).tobytes()

    def transform(imdP, imd, points, maxdif):
        imgd = imdP
        iml = len(imgd)
        bio = BytesIO()
        for pix in range(0, iml, points):
            _imd = imgd[pix:pix+points]
            dif = max(_imd)-min(_imd)
            if dif <= maxdif: bio.write(make(imd[pix*3:pix*3+points*3])); continue
            bio.write(imd[pix*3:pix*3+points*3])
        return bio.getvalue()

    if image_mode < 2:

        if debug:
            print('OPENING IMAGE...')

        im = Image.open(imf)
        if image_mode == 0:
            im = im.convert('RGB')

        if debug:
            print('SCALING IMAGE...')

        ims = im.size[0]*3
        if quality_x == 3:
            pass
        elif quality_x == 2:
            im = cutsize(im, 2)
        elif quality_x == 1:
            im = cutsize(im, 4)
        elif quality_x == 0:
            im = cutsize(im, 6)
        else:
            pass

        if image_mode == 1:
            im = im.convert('RGBA')
            alpha = im.split()[-1]
            alpha = list(alpha.convert('L').getdata())
            im = im.convert('RGB')

        if debug:
            print('OPTIMIZING IMAGE...')

        if optimizer_enabled:
            im = Image.frombytes(data=transform(im.convert('P').tobytes(), im.tobytes(), optimizer_chunk, optimizer_maxdiff), mode=im.mode, size=im.size)

        if debug:
            print('CREATING IMAGE WITH COLOR SPACE...')

        if quality_y == 7:
            img = create_img(im, 2) # 2097152 color mode
        elif quality_y == 6:
            img = create_img(im, 3) # 614125 color mode
        elif quality_y == 5:
            img = create_img(im, 4) # 262144 color mode
        elif quality_y == 4:
            img = create_img(im, 6) # 74088 color mode
        elif quality_y == 3:
            img = create_img(im, 8) # 32768 color mode
        elif quality_y == 2:
            img = create_img(im, 12) # 9261 color mode
        elif quality_y == 1:
            img = create_img(im, 16) # 4096 color mode
        elif quality_y == 0:
            img = create_img(im, 32) # 512 color mode

        if not quiet:
            if im.size[0]*im.size[1] > 2073600:
                print('MAPF WARNING:', warns[0])
        if not quiet:
            if image_mode in (1,6):
                if im.size[0]*im.size[1]*4 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*4*6)//1000000))
            else:
                if im.size[0]*im.size[1]*3 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*3*6)//1000000))

        imb = img.tobytes()
        lb = len(imb)
        bio = BytesIO()
        oclr = bytes(0)
        o2clr = bytes(0)
        o3clr = bytes(0)
        o4clr = bytes(0)
        o5clr = bytes(0)
        o6clr = bytes(0)
        o7clr = bytes(0)
        o8clr = bytes(0)

        if debug:
            print('INTERNAL COMPRESSING...')

        for rd in range(0, lb, 3):
            clr = imb[rd:rd+3]
            if rd >= 3: oclr = imb[rd-3:rd]
            if rd >= 6: o2clr = imb[rd-6:rd-3]
            if rd >= 9: o3clr = imb[rd-9:rd-6]
            if rd >= 12: o4clr = imb[rd-12:rd-9]
            if rd >= 15: o5clr = imb[rd-15:rd-12]
            if rd >= 18: o6clr = imb[rd-18:rd-15]
            if rd >= 21: o7clr = imb[rd-21:rd-18]
            if rd >= 24: o8clr = imb[rd-24:rd-21]
            if clr == oclr:
                bio.write(SAME_CLR)
                continue
            if clr == bytes(3):
                bio.write(BK_CLR)
                continue
            if clr == bytes([127,127,127]):
                bio.write(WT_CLR)
                continue

            if clr == o2clr:
                bio.write(_2BC_SAME)
                continue
            if clr == o3clr:
                bio.write(_3BC_SAME)
                continue
            if clr == o4clr:
                bio.write(_4BC_SAME)
                continue
            if clr == o5clr:
                bio.write(_5BC_SAME)
                continue
            if clr == o6clr:
                bio.write(_6BC_SAME)
                continue
            if clr == o7clr:
                bio.write(_7BC_SAME)
                continue
            if clr == o8clr:
                bio.write(_8BC_SAME)
                continue
            if len(clr) == 3 and len(oclr) == 3:
                if 255-clr[0] == oclr[0] and 255-clr[1] == oclr[1] and 255-clr[2] == oclr[2]:
                    bio.write(NEGATIVE_CLR)
                    continue

                if abs(clr[0]-oclr[0]) <= 1 and abs(clr[1]-oclr[1]) <= 1 and abs(clr[2]-oclr[2]) <= 1:
                    if oclr[0] == clr[0] and oclr[1] == clr[1] and oclr[2]-1 == clr[2]:
                        bio.write(p0p0m1_BRIGHTNESS)
                        continue
                    if oclr[0] == clr[0] and oclr[1]-1 == clr[1] and oclr[2]-1 == clr[2]:
                        bio.write(p0m1m1_BRIGHTNESS)
                        continue
                    if oclr[0]-1 == clr[0] and oclr[1]-1 == clr[1] and oclr[2]-1 == clr[2]:
                        bio.write(m1m1m1_BRIGHTNESS)
                        continue
                    if oclr[0]-1 == clr[0] and oclr[1]-1 == clr[1] and oclr[2] == clr[2]:
                        bio.write(m1m1p0_BRIGHTNESS)
                        continue
                    if oclr[0]-1 == clr[0] and oclr[1] == clr[1] and oclr[2] == clr[2]:
                        bio.write(m1p0p0_BRIGHTNESS)
                        continue
                    if oclr[0]-1 == clr[0] and oclr[1] == clr[1] and oclr[2]-1 == clr[2]:
                        bio.write(m1p0m1_BRIGHTNESS)
                        continue
                    if oclr[0] == clr[0] and oclr[1]-1 == clr[1] and oclr[2] == clr[2]:
                        bio.write(p0m1p0_BRIGHTNESS)
                        continue

                    if oclr[0] == clr[0] and oclr[1] == clr[1] and oclr[2]+1 == clr[2]:
                        bio.write(p0p0p1_BRIGHTNESS)
                        continue
                    if oclr[0] == clr[0] and oclr[1]+1 == clr[1] and oclr[2]+1 == clr[2]:
                        bio.write(p0p1p1_BRIGHTNESS)
                        continue
                    if oclr[0]+1 == clr[0] and oclr[1]+1 == clr[1] and oclr[2]+1 == clr[2]:
                        bio.write(p1p1p1_BRIGHTNESS)
                        continue
                    if oclr[0]+1 == clr[0] and oclr[1]+1 == clr[1] and oclr[2] == clr[2]:
                        bio.write(p1p1p0_BRIGHTNESS)
                        continue
                    if oclr[0]+1 == clr[0] and oclr[1] == clr[1] and oclr[2] == clr[2]:
                        bio.write(p1p0p0_BRIGHTNESS)
                        continue
                    if oclr[0]+1 == clr[0] and oclr[1] == clr[1] and oclr[2]+1 == clr[2]:
                        bio.write(p1p0p1_BRIGHTNESS)
                        continue
                    if oclr[0] == clr[0] and oclr[1]+1 == clr[1] and oclr[2] == clr[2]:
                        bio.write(p0p1p0_BRIGHTNESS)
                        continue

                    if oclr[0]-1 == clr[0] and oclr[1]-1 == clr[1] and oclr[2]+1 == clr[2]:
                        bio.write(m1m1p1_BRIGHTNESS)
                        continue
                    if oclr[0]-1 == clr[0] and oclr[1] == clr[1] and oclr[2]+1 == clr[2]:
                        bio.write(m1p0p1_BRIGHTNESS)
                        continue
                    if oclr[0]-1 == clr[0] and oclr[1]+1 == clr[1] and oclr[2]-1 == clr[2]:
                        bio.write(m1p1m1_BRIGHTNESS)
                        continue
                    if oclr[0]-1 == clr[0] and oclr[1]+1 == clr[1] and oclr[2] == clr[2]:
                        bio.write(m1p1p0_BRIGHTNESS)
                        continue
                    if oclr[0]-1 == clr[0] and oclr[1]+1 == clr[1] and oclr[2]+1 == clr[2]:
                        bio.write(m1p1p1_BRIGHTNESS)
                        continue
                    if oclr[0] == clr[0] and oclr[1]-1 == clr[1] and oclr[2]+1 == clr[2]:
                        bio.write(p0m1p1_BRIGHTNESS)
                        continue
                    if oclr[0] == clr[0] and oclr[1]+1 == clr[1] and oclr[2]-1 == clr[2]:
                        bio.write(p0p1m1_BRIGHTNESS)
                        continue
                    if oclr[0]+1 == clr[0] and oclr[1]-1 == clr[1] and oclr[2]-1 == clr[2]:
                        bio.write(p1m1m1_BRIGHTNESS)
                        continue
                    if oclr[0]+1 == clr[0] and oclr[1]-1 == clr[1] and oclr[2] == clr[2]:
                        bio.write(p1m1p0_BRIGHTNESS)
                        continue
                    if oclr[0]+1 == clr[0] and oclr[1]-1 == clr[1] and oclr[2]+1 == clr[2]:
                        bio.write(p1m1p1_BRIGHTNESS)
                        continue
                    if oclr[0]+1 == clr[0] and oclr[1] == clr[1] and oclr[2]-1 == clr[2]:
                        bio.write(p1p0m1_BRIGHTNESS)
                        continue
                    if oclr[0]+1 == clr[0] and oclr[1]+1 == clr[1] and oclr[2]-1 == clr[2]:
                        bio.write(p1p1m1_BRIGHTNESS)
                        continue

                if oclr[0]+2 == clr[0] and oclr[1]+2 == clr[1] and oclr[2]+2 == clr[2]:
                    bio.write(p2_BRIGHTNESS)
                    continue
                if oclr[0]+3 == clr[0] and oclr[1]+3 == clr[1] and oclr[2]+3 == clr[2]:
                    bio.write(p3_BRIGHTNESS)
                    continue
                if oclr[0]+4 == clr[0] and oclr[1]+4 == clr[1] and oclr[2]+4 == clr[2]:
                    bio.write(p4_BRIGHTNESS)
                    continue
                if oclr[0]+5 == clr[0] and oclr[1]+5 == clr[1] and oclr[2]+5 == clr[2]:
                    bio.write(p5_BRIGHTNESS)
                    continue

                if oclr[0]-2 == clr[0] and oclr[1]-2 == clr[1] and oclr[2]-2 == clr[2]:
                    bio.write(m2_BRIGHTNESS)
                    continue
                if oclr[0]-3 == clr[0] and oclr[1]-3 == clr[1] and oclr[2]-3 == clr[2]:
                    bio.write(m3_BRIGHTNESS)
                    continue
                if oclr[0]-4 == clr[0] and oclr[1]-4 == clr[1] and oclr[2]-4 == clr[2]:
                    bio.write(m4_BRIGHTNESS)
                    continue
                if oclr[0]-5 == clr[0] and oclr[1]-5 == clr[1] and oclr[2]-5 == clr[2]:
                    bio.write(m5_BRIGHTNESS)
                    continue

            if clr == bytes([127,0,0]):
                bio.write(RD_CLR)
                continue
            if clr == bytes([0,127,0]):
                bio.write(GR_CLR)
                continue
            if clr == bytes([0,0,127]):
                bio.write(BL_CLR)
                continue
            bio.write(clr)

    elif image_mode == 2:

        if debug:
            print('CREATING LOSSLESS IMAGE...')
        quality_x = quality_y = 0
        im = Image.open(imf)
        if not quiet:
            if image_mode in (1,6):
                if im.size[0]*im.size[1]*4 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*4*6)//1000000))
            else:
                if im.size[0]*im.size[1]*3 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*3*6)//1000000))
        if debug:
            print('SPLITTING CHANNELS...')
        Y, U, V = im.convert('YCbCr').split() # YUV
        bio = BytesIO()
        lb = bio.write(Y.tobytes()+U.tobytes()+V.tobytes())

    elif image_mode == 3:

        if debug:
            print('OPENING IMAGE...')
            
        im = Image.open(imf).convert('RGB')

        if not quiet:
            if image_mode in (1,6):
                if im.size[0]*im.size[1]*4 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*4*6)//1000000))
            else:
                if im.size[0]*im.size[1]*3 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*3*6)//1000000))
        
        im = im.convert('YCbCr')

        bio = BytesIO()
        if quality_z == 15:
            div_y = 1
            div_u = 1
            div_v = 1
        elif quality_z == 14:
            div_y = 1
            div_u = 1
            div_v = 2
        elif quality_z == 13:
            div_y = 1
            div_u = 2
            div_v = 2
        elif quality_z == 12:
            div_y = 1
            div_u = 2
            div_v = 4
        elif quality_z == 11:
            div_y = 1
            div_u = 4
            div_v = 4
        elif quality_z == 10:
            div_y = 1
            div_u = 4
            div_v = 6
        elif quality_z == 9:
            div_y = 1
            div_u = 6
            div_v = 6
        elif quality_z == 8:
            div_y = 1
            div_u = 6
            div_v = 8
        elif quality_z == 7:
            div_y = 1
            div_u = 8
            div_v = 8
        elif quality_z == 6:
            div_y = 1
            div_u = 12
            div_v = 12
        elif quality_z == 5:
            div_y = 1
            div_u = 16
            div_v = 16
        elif quality_z == 4:
            div_y = 1
            div_u = 32
            div_v = 32
        elif quality_z == 3:
            div_y = 2
            div_u = 4
            div_v = 4
        elif quality_z == 2:
            div_y = 2
            div_u = 8
            div_v = 8
        elif quality_z == 1:
            div_y = 2
            div_u = 12
            div_v = 12
        elif quality_z == 0:
            div_y = 2
            div_u = 16
            div_v = 16
        else:
            div_y = 1
            div_u = 1
            div_v = 1

        if debug:
            print('SPLITTING CHANNELS...')
        y, u, v = im.split()

        if debug:
            print('CREATING LOSSY IMAGE...')
        color_dividors = [32.0,16.0,12.0,8.0,4.0,2.0,1.340,1.143]
        cdiv = color_dividors[quality_y]
        size = y.size
        try:
            y = (numpy.array(list(y.resize((size[0]//div_y, size[1]//div_y), enlargers[enlarger]).getdata()), dtype=numpy.float16)/cdiv).astype(numpy.uint8)
            u = (numpy.array(list(u.resize((size[0]//div_u, size[1]//div_u), enlargers[enlarger]).getdata()), dtype=numpy.float16)/cdiv).astype(numpy.uint8)
            v = (numpy.array(list(v.resize((size[0]//div_v, size[1]//div_v), enlargers[enlarger]).getdata()), dtype=numpy.float16)/cdiv).astype(numpy.uint8)
        except ValueError:
            if __name__ == '__main__':
                print('MAPF ERROR:', errors[12])
                sys.exit(16)
            else:
                raise MAPFException(errors[12])
        if debug:
            print('WRITING OUT IMAGE...')
        
        bio.write(y.tobytes()+u.tobytes()+v.tobytes())
        del y,u,v

    elif image_mode == 4:

        if debug:
            print('OPENING IMAGE...')
        im = Image.open(imf)
        if not quiet:
            if image_mode in (1,6):
                if im.size[0]*im.size[1]*4 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*4*6)//1000000))
            else:
                if im.size[0]*im.size[1]*3 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*3*6)//1000000))
        if debug:
            print('CHANGING IMAGE TO MODE LUMA...')
        im = im.convert('L')
        if quality_x == 3:
            pass
        elif quality_x == 2:
            im = cutsize(im, 2)
        elif quality_x == 1:
            im = cutsize(im, 4)
        elif quality_x == 0:
            im = cutsize(im, 6)
        else:
            pass
        imb = im.tobytes()
        if debug:
            print('CREATING LOSSY IMAGE...')
        if quality_y != 7:
            color_dividors = [32.0,16.0,12.0,8.0,4.0,2.0,1.340,1.0]
            cdiv = color_dividors[quality_y]
            imb = (numpy.array(list(im.getdata()), dtype=numpy.float16)/cdiv).astype(numpy.uint8)
            imb = imb.tobytes()
        bio = BytesIO()
        bio.write(imb)
        del imb

    elif image_mode == 5:

        if debug:
            print('OPENING IMAGE...')
        im = Image.open(imf).convert('RGB')
        enlarger = enlargers[enlarger]

        if not quiet:
            if image_mode in (1,6):
                if im.size[0]*im.size[1]*4 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*4*6)//1000000))
            else:
                if im.size[0]*im.size[1]*3 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*3*6)//1000000))

        try:

            if debug:
                print('RESIZING IMAGE...')
            if quality_x == 3:
                im = im.resize((im.size[0]//2, im.size[1]//2), enlarger)
            elif quality_x == 2:
                im = im.resize((im.size[0]//8, im.size[1]//8), enlarger)
            elif quality_x == 1:
                im = im.resize((im.size[0]//16, im.size[1]//16), enlarger)
            else:
                im = im.resize((im.size[0]//64, im.size[1]//64), enlarger)

        except ValueError:
            if __name__ == '__main__':
                print('MAPF ERROR:', errors[12])
                sys.exit(16)
            else:
                raise MAPFException(errors[12])

        _prev_colors = [128, 64, 48, 32, 16, 12, 8, 4]
        if debug:
            print('CREATING DRAFT IMAGE...')
        imb = create_img(im, _prev_colors[quality_y]).tobytes()
        bio = BytesIO()
        bio.write(imb)
        del imb

    elif image_mode == 6:

        if debug:
            print('CREATING LOSSLESS IMAGE...')
        im = Image.open(imf)
        if not quiet:
            if image_mode in (1,6):
                if im.size[0]*im.size[1]*4 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*4*6)//1000000))
            else:
                if im.size[0]*im.size[1]*3 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*3*6)//1000000))
        A = im.convert('RGBA').split()[-1]
        if debug:
            print('SPLITTING CHANNELS...')
        Y, U, V = im.convert('YCbCr').split() # YUV
        bio = BytesIO()
        bio.write(Y.tobytes()+U.tobytes()+V.tobytes()+A.tobytes())

    elif image_mode == 7:
        im = Image.open(imf).convert('YCbCr')
        if not quiet:
            if image_mode in (1,6):
                if im.size[0]*im.size[1]*4 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*4*6)//1000000))
            else:
                if im.size[0]*im.size[1]*3 >= 300000000:
                    print('MAPF WARNING:', warns[2].format((im.size[0]*im.size[1]*3*6)//1000000))
        w,h = im.size
        bio = BytesIO()
        hints = BytesIO()
        tquality = m7_quality[quality]
        color_dividors = [32.0,16.0,12.0,8.0,4.0,2.0,1.340,1.143]
        sens = [(200, 240, 250), (190, 210, 230), (180, 200, 220), (150, 180, 200), (130, 150, 180), (110, 120, 150), (75, 100, 120), (25,50,75), (15,40,75), (10,40,60), (10, 30, 50), (5,20,40), (2,10,20), (2,5,20), (2,3,10), (2,3,4)]
        quality_y = tquality//16
        qual = tquality%8

        for x in range(0, h, 16):
            for y in range(0, w, 16):
                img = im.crop((y, x, y+16, x+16))
                Y, Cb, Cr = img.split()
                _xlen = list(img.convert('L').tobytes())
                xlen = abs(max(_xlen)-min(_xlen))

                if xlen <= sens[qual][0]:
                    hints.write(bytes([0]))
                    _y, _cb, _cr = img.resize((2,2)).split()
                    bio.write(_y.tobytes()+_cb.tobytes()+_cr.tobytes())
                    continue
                if xlen <= sens[qual][1]:
                    hints.write(bytes([1]))
                    _y, _cb, _cr = img.resize((4,4)).split()
                    bio.write(_y.tobytes()+_cb.tobytes()+_cr.tobytes())
                    continue
                if xlen <= sens[qual][2]:
                    hints.write(bytes([2]))
                    _y, _cb, _cr = img.resize((8,8)).split()
                    bio.write(_y.tobytes()+_cb.tobytes()+_cr.tobytes())
                    continue
                hints.write(bytes([3]))
                bio.write(Y.tobytes()+Cb.tobytes()+Cr.tobytes())

        cdiv = color_dividors[quality_y]
        imb = (numpy.array(list(bio.getvalue()), dtype=numpy.float16)/cdiv).astype(numpy.uint8)
        bio = BytesIO()
        limb = len(imb)
        bio.write(imb)
        bio.write(hints.getvalue())
        hints.close()
        del imb
    
    if debug:
        print('WRITING METADATA...')

    if image_mode != 3:
        if image_mode > 3:
            if not image_mode == 7:
                header = b'ma'+bitstruct.pack('u3u3u2', release, compress_mode, image_mode-4)+bitstruct.pack('u2u4u2', quality_x, quality_y, enlarger)+struct.pack('>H', im.size[0])+struct.pack('>I', len(bio.getvalue()))
            else:
                header = b'ma'+bitstruct.pack('u3u3u2', release, compress_mode, image_mode-4)+bitstruct.pack('u2u4u2', quality_x, quality_y, enlarger)+struct.pack('>H', im.size[0])+struct.pack('>H', im.size[1])+struct.pack('>I', limb)
        else:
            header = b'mA'+bitstruct.pack('u3u3u2', release, compress_mode, image_mode)+bitstruct.pack('u2u4u2', quality_x, quality_y, enlarger)+struct.pack('>H', im.size[0])+struct.pack('>I', lb)
    else:
        header = b'MA'+bitstruct.pack('u3u3u2', release, compress_mode, enlarger)+bitstruct.pack('u4u4', quality_z, quality_y)+struct.pack('>H', im.size[0])+struct.pack('>I', im.size[1])
    if not return_data:
        af = open(outf, 'wb')
        af.write(header)
        af.close()
        _outf = outf
    else:
        af = BytesIO()
        af.write(header)
        outf = af
        _outf = 'tmp'
    if image_mode == 1:
        if debug:
            print('WRITING ALPHA CHANNEL...')
        bio.write((numpy.array(alpha,dtype=numpy.uint8)//2).tobytes())

    if image_mode in (3,4) and helper:
        if bio.tell() < compress_helper_max*(1024**2):
            _bio = BytesIO()
            if debug:
                print('RUNNING COMPRESSION HELPER...')
            bio.seek(0)
            cnt = 0
            while True:
                block = bio.read(3)
                if len(block) != 3:
                    _bio.write(block)
                    break
                if block[0] == block[2]:
                    _bio.write(bytes([block[0]]*3))
                    cnt += 2
                else:
                    _bio.write(block)
                cnt += 1
                bio.seek(cnt)
                _bio.seek(cnt)
            bio.close()
            del bio
            bio = _bio
            del _bio

    if debug:
        print('EXTERNAL COMPRESSING...')

    bio.seek(0)

    if compress_mode == 0:
        with bio as inpt:
            with lzma.LZMAFile(outf, 'ab', preset=compress_power) as output:
                copyfileobj(inpt, output)
    if compress_mode == 1:
        with bio as inpt:
            with bz2.BZ2File(outf, 'ab', compresslevel=compress_power) as output:
                copyfileobj(inpt, output)
    if compress_mode == 2:
        if debug:
            print('USING NANOZIP BINARY WRITTEN BY Sami Runsas from http://nanozip.ijat.my/.')
        if not os.path.exists(relative_path('nz.exe')):
            if __name__ == '__main__':
                print('MAPF ERROR:', errors[13])
                sys.exit(17)
            else:
                raise MAPFException(errors[13])
        _tmpfile = open(_outf+'.tmp', 'wb')
        _tmpfile.write(bio.getvalue())
        _tmpfile.close()
        p = subprocess.Popen('"{}" a "{}" "{}" -cc -nm -y -sp >nul'.format(relative_path('nz.exe'), _outf+'.nz', _outf+'.tmp'), stdout=subprocess.PIPE, shell=True)
        (soutput, err) = p.communicate()  
        p_status = p.wait()
        try: os.remove(_outf+'.tmp')
        except: pass
        bcmed = open(_outf+'.nz', 'rb')
        if not return_data:
            outfile = open(_outf, 'ab')
            outfile.write(bcmed.read())
            bcmed.close()
            outfile.close()
        else:
            outf.write(bcmed.read())
        try: os.remove(_outf+'.nz')
        except: pass
        if debug:
            print('COMPRESSED BY NANOZIP, ERROR: {}'.format(err))
    if compress_mode == 3:
        outfile = open(outf, 'ab')
        outfile.write(brotli.compress(bio.getvalue(), quality=compress_power))
        outfile.close()
    if compress_mode == 4:
        outfile = open(outf, 'ab')
        outfile.write(zstd.compress(bio.getvalue(), compress_power))
        outfile.close()
    if compress_mode == 5:
        outfile = open(outf, 'ab')
        outfile.write(snappy.compress(bio.getvalue()))
        outfile.close()
    if compress_mode == 6:
        outfile = open(outf, 'ab')
        outfile.write(bio.getvalue())
        outfile.close()
    if compress_mode == 7:
        if debug:
            print('USING BCM BINARY WRITTEN BY Ilya Muravyov from https://github.com/encode84.')
        if not os.path.exists(relative_path('bcm.exe')):
            if __name__ == '__main__':
                print('MAPF ERROR:', errors[10])
                sys.exit(14)
            else:
                raise MAPFException(errors[10])
        _tmpfile = open(_outf+'.tmp', 'wb')
        _tmpfile.write(bio.getvalue())
        _tmpfile.close()
        p = subprocess.Popen('"{}" -b1 -f "{}" "{}"'.format(relative_path('bcm.exe'), _outf+'.tmp', _outf+'.bcm'), stdout=subprocess.PIPE, shell=True)
        (soutput, err) = p.communicate()  
        p_status = p.wait()
        try: os.remove(_outf+'.tmp')
        except: pass
        bcmed = open(_outf+'.bcm', 'rb')
        if not return_data:
            outfile = open(_outf, 'ab')
            outfile.write(bcmed.read())
            bcmed.close()
            outfile.close()
        else:
            outf.write(bcmed.read())
        try: os.remove(_outf+'.bcm')
        except: pass
        if debug:
            print('COMPRESSED BY BCM, OUTPUT: {}, ERROR: {}'.format(soutput,err))

    if not quiet:
        print('Output image generated in:', time.time()-time_old, 'seconds.')
        if not return_data:
            print('Size difference: "{}" {} --> "{}" {}'.format(input_path, human_size(os.stat(input_path).st_size), output_path, human_size(os.stat(output_path).st_size)))

    if return_data:
        if not quiet:
            print('Size difference: "{}" {} --> "{}" {}'.format(input_path, human_size(os.stat(input_path).st_size), output_path, human_size(len(af.getvalue()))))
        return af.getvalue()
    else:
        return True

def read(input_image, output_image=None, showonly=True, debug=True, quiet=False):
    told = time.time()
    outi = output_image
    MAPFfile = input_image
    del input_image

    if debug:
        print('OPENING IMAGE...')

    if type(MAPFfile) != _io.BytesIO: 
        if not os.path.exists(MAPFfile):
            if __name__ == '__main__':
                print('MAPF ERROR:', errors[4])
                sys.exit(11)
            else:
                raise MAPFException(errors[4])
        f = open(MAPFfile, 'rb')
    else:
        f = MAPFfile
        f.seek(0)
        del MAPFfile
    imtype = f.read(2)
    if imtype not in (b'mA', b'MA', b'ma'):
        if __name__ == '__main__':
            print('MAPF ERROR:', errors[1])
            sys.exit(3)
        else:
            raise MAPFException(errors[1])

    if debug:
        print('READING METADATA...')

    if imtype == b'mA':
        release, compress_mode, image_mode = bitstruct.unpack('u3u3u2', f.read(1))
    elif imtype == b'ma':
        release, compress_mode, image_mode = bitstruct.unpack('u3u3u2', f.read(1))
        image_mode += 4
    else:
        release, compress_mode, _enlarger = bitstruct.unpack('u3u3u2', f.read(1))
        image_mode = 3
    if image_mode > 7:
        if __name__ == '__main__':
            print('MAPF ERROR:', errors[0])
            sys.exit(4)
        else:
            raise MAPFException(errors[0])
    if imtype in (b'ma', b'Ma', b'mA'):
        quality_x, quality_y, _enlarger = bitstruct.unpack('u2u4u2', f.read(1))
    else:
        quality_z, quality_y = bitstruct.unpack('u4u4', f.read(1))
        if quality_z == 15:
            div_y = 1
            div_u = 1
            div_v = 1
        elif quality_z == 14:
            div_y = 1
            div_u = 1
            div_v = 2
        elif quality_z == 13:
            div_y = 1
            div_u = 2
            div_v = 2
        elif quality_z == 12:
            div_y = 1
            div_u = 2
            div_v = 4
        elif quality_z == 11:
            div_y = 1
            div_u = 4
            div_v = 4
        elif quality_z == 10:
            div_y = 1
            div_u = 4
            div_v = 6
        elif quality_z == 9:
            div_y = 1
            div_u = 6
            div_v = 6
        elif quality_z == 8:
            div_y = 1
            div_u = 6
            div_v = 8
        elif quality_z == 7:
            div_y = 1
            div_u = 8
            div_v = 8
        elif quality_z == 6:
            div_y = 1
            div_u = 12
            div_v = 12
        elif quality_z == 5:
            div_y = 1
            div_u = 16
            div_v = 16
        elif quality_z == 4:
            div_y = 1
            div_u = 32
            div_v = 32
        elif quality_z == 3:
            div_y = 2
            div_u = 4
            div_v = 4
        elif quality_z == 2:
            div_y = 2
            div_u = 8
            div_v = 8
        elif quality_z == 1:
            div_y = 2
            div_u = 12
            div_v = 12
        elif quality_z == 0:
            div_y = 2
            div_u = 16
            div_v = 16
        else:
            div_y = 1
            div_u = 1
            div_v = 1
    size_w = struct.unpack('>H', f.read(2))[0]
    if image_mode != 7:
        if imtype == b'mA':
            datalen = struct.unpack('>I', f.read(4))[0]
            size_h = int(datalen/size_w/3)
            if size_h != datalen/size_w/3:
                if __name__ == '__main__':
                    print('MAPF ERROR:', errors[2])
                    sys.exit(5)
                else:
                    raise MAPFException(errors[2])
        else:
            size_h = struct.unpack('>I', f.read(4))[0]
    else:
        size_h = struct.unpack('>H', f.read(2))[0]
        datalen = struct.unpack('>I', f.read(4))[0]

    packed = f.read()

    if debug:
        print('DECOMPRESSING EXTERNAL...')

    if compress_mode == 0:
        data = lzma.decompress(packed)
    elif compress_mode == 1:
        data = bz2.decompress(packed)
    elif compress_mode == 2:
        if debug:
            print('USING NANOZIP BINARY WRITTEN BY Sami Runsas from http://nanozip.ijat.my/.')
        if not os.path.exists(relative_path('nz.exe')):
            if __name__ == '__main__':
                print('MAPF ERROR:', errors[13])
                sys.exit(17)
            else:
                raise MAPFException(errors[13])
        bcmdata = open('MAPFtemp{}.nz'.format(os.getpid()), 'wb')
        bcmdata.write(packed)
        bcmdata.close()
        p = subprocess.Popen('"{}" x "{}" -o"{}" -y >nul'.format(relative_path('nz.exe'), 'MAPFtemp{}.nz'.format(os.getpid()), 'MAPFtemp{}'.format(os.getpid())), stdout=subprocess.PIPE, shell=True)
        (soutput, err) = p.communicate()  
        p_status = p.wait()
        _fname = os.listdir('MAPFtemp{}'.format(os.getpid()))[0]
        _data = open('MAPFtemp{}/{}'.format(os.getpid(), _fname), 'rb')
        data = _data.read()
        _data.close()
        try: os.remove('MAPFtemp{}/{}'.format(os.getpid(), _fname))
        except: pass
        try: os.remove('MAPFtemp{}.nz'.format(os.getpid()))
        except: pass
        try: os.rmdir('MAPFtemp{}'.format(os.getpid()))
        except: pass
        if debug:
            print('DECOMPRESSED BY NANOZIP, ERROR: {}'.format(err))
    elif compress_mode == 3:
        data = brotli.decompress(packed)
    elif compress_mode == 4:
        data = zstd.decompress(packed)
    elif compress_mode == 5:
        data = snappy.decompress(packed)
    elif compress_mode == 6:
        data = packed
    elif compress_mode == 7:
        if debug:
            print('USING BCM BINARY WRITTEN BY Ilya Muravyov from https://github.com/encode84.')
        if not os.path.exists(relative_path('bcm.exe')):
            if __name__ == '__main__':
                print('MAPF ERROR:', errors[10])
                sys.exit(14)
            else:
                raise MAPFException(errors[10])
        bcmdata = open('MAPFtemp{}.bcm'.format(os.getpid()), 'wb')
        bcmdata.write(packed)
        bcmdata.close()
        p = subprocess.Popen('"{}" -d -f "{}" "{}"'.format(relative_path('bcm.exe'), 'MAPFtemp{}.bcm'.format(os.getpid()), 'MAPFtemp{}.tmp'.format(os.getpid())), stdout=subprocess.PIPE, shell=True)
        (soutput, err) = p.communicate()  
        p_status = p.wait()
        _data = open('MAPFtemp{}.tmp'.format(os.getpid()), 'rb')
        data = _data.read()
        _data.close()
        try: os.remove('MAPFtemp{}.tmp'.format(os.getpid()))
        except: pass
        try: os.remove('MAPFtemp{}.bcm'.format(os.getpid()))
        except: pass
        if debug:
            print('DECOMPRESSED BY BCM, OUTPUT: {}, ERROR: {}'.format(soutput,err))
    else:
        if __name__ == '__main__':
            print('MAPF ERROR:', errors[3])
            sys.exit(6)
        else:
            raise MAPFException(errors[3])

    if image_mode == 1:
        if debug:
            print('SPLITTING ALPHA AND RGB DATA...')
        dlen = len(data)-size_w*size_h
        alpha = data[dlen:]
        data = data[:dlen]

    del packed
    bio = BytesIO()

    if image_mode < 2:

        cnt = 0
        ims = size_w*3
        ndata = data

        if debug:
            print('EQUATION DATA length...')

        for x in range(128, 178, 1):
            ndata = ndata.replace(bytes([x]), bytes([x,x,x]))

        lnd = len(ndata)
        old = bytes(3)
        o2 = o3 = o4 = o5 = o6 = o7 = o8 = o1 = 0

        if debug:
            print('DECOMPRESSING INTERNAL...')

        for num in range(0, lnd, 3):
            o8 = o7
            o7 = o6
            o6 = o5
            o5 = o4
            o4 = o3
            o3 = o2
            o2 = o1
            o1 = old

            cur = ndata[num:num+3]
            if cur[0] < 128:
                old = cur
                bio.write(cur)
                continue

            if cur[0] == 128:
                old = bytes(3)
                bio.write(old)
                continue
            if cur[0] == 129:
                old = bytes([127,127,127])
                bio.write(old)
                continue
            if cur[0] == 130:
                bio.write(old)
                continue

            if cur[0] == 136:
                old = bytes([old[0], old[1], old[2]-1])
                bio.write(old)
                continue
            if cur[0] == 137:
                old = bytes([old[0], old[1]-1, old[2]-1])
                bio.write(old)
                continue
            if cur[0] == 138:
                old = bytes([old[0]-1, old[1]-1, old[2]-1])
                bio.write(old)
                continue
            if cur[0] == 139:
                old = bytes([old[0]-1, old[1], old[2]])
                bio.write(old)
                continue
            if cur[0] == 140:
                old = bytes([old[0]-1, old[1]-1, old[2]])
                bio.write(old)
                continue
            if cur[0] == 141:
                old = bytes([old[0]-1, old[1], old[2]-1])
                bio.write(old)
                continue
            if cur[0] == 142:
                old = bytes([old[0], old[1]-1, old[2]])
                bio.write(old)
                continue

            if cur[0] == 143:
                old = o2
                bio.write(old)
                continue
            if cur[0] == 144:
                old = o3
                bio.write(old)
                continue
            if cur[0] == 145:
                old = o4
                bio.write(old)
                continue
            if cur[0] == 146:
                old = o5
                bio.write(old)
                continue
            if cur[0] == 147:
                old = o6
                bio.write(old)
                continue

            if cur[0] == 148:
                old = o7
                bio.write(old)
                continue

            if cur[0] == 149:
                old = o8
                bio.write(old)
                continue

            if cur[0] == 150:
                old = bytes([old[0]+2, old[1]+2, old[2]+2])
                bio.write(old)
                continue
            if cur[0] == 151:
                old = bytes([old[0]-2, old[1]-2, old[2]-2])
                bio.write(old)
                continue
            if cur[0] == 152:
                old = bytes([old[0]+3, old[1]+3, old[2]+3])
                bio.write(old)
                continue
            if cur[0] == 153:
                old = bytes([old[0]-3, old[1]-3, old[2]-3])
                bio.write(old)
                continue
            if cur[0] == 154:
                old = bytes([old[0]+4, old[1]+4, old[2]+4])
                bio.write(old)
                continue
            if cur[0] == 155:
                old = bytes([old[0]-4, old[1]-4, old[2]-4])
                bio.write(old)
                continue
            if cur[0] == 156:
                old = bytes([old[0]+5, old[1]+5, old[2]+5])
                bio.write(old)
                continue
            if cur[0] == 157:
                old = bytes([old[0]-5, old[1]-5, old[2]-5])
                bio.write(old)
                continue

            if cur[0] == 159:
                old = bytes([old[0], old[1], old[2]+1])
                bio.write(old)
                continue
            if cur[0] == 160:
                old = bytes([old[0], old[1]+1, old[2]+1])
                bio.write(old)
                continue
            if cur[0] == 161:
                old = bytes([old[0]+1, old[1]+1, old[2]+1])
                bio.write(old)
                continue
            if cur[0] == 162:
                old = bytes([old[0]+1, old[1], old[2]])
                bio.write(old)
                continue
            if cur[0] == 163:
                old = bytes([old[0]+1, old[1]+1, old[2]])
                bio.write(old)
                continue
            if cur[0] == 164:
                old = bytes([old[0]+1, old[1], old[2]+1])
                bio.write(old)
                continue
            if cur[0] == 165:
                old = bytes([old[0], old[1]+1, old[2]])
                bio.write(old)
                continue

            if cur[0] == 166:
                old = bytes([old[0]-1, old[1]-1, old[2]+1])
                bio.write(old)
                continue
            if cur[0] == 167:
                old = bytes([old[0]-1, old[1], old[2]+1])
                bio.write(old)
                continue
            if cur[0] == 168:
                old = bytes([old[0]-1, old[1]+1, old[2]-1])
                bio.write(old)
                continue
            if cur[0] == 169:
                old = bytes([old[0]-1, old[1]+1, old[2]])
                bio.write(old)
                continue
            if cur[0] == 170:
                old = bytes([old[0]-1, old[1]+1, old[2]+1])
                bio.write(old)
                continue
            if cur[0] == 171:
                old = bytes([old[0], old[1]-1, old[2]+1])
                bio.write(old)
                continue
            if cur[0] == 172:
                old = bytes([old[0], old[1]+1, old[2]-1])
                bio.write(old)
                continue
            if cur[0] == 173:
                old = bytes([old[0]+1, old[1]-1, old[2]-1])
                bio.write(old)
                continue
            if cur[0] == 174:
                old = bytes([old[0]+1, old[1]-1, old[2]])
                bio.write(old)
                continue
            if cur[0] == 175:
                old = bytes([old[0]+1, old[1]-1, old[2]+1])
                bio.write(old)
                continue
            if cur[0] == 176:
                old = bytes([old[0]+1, old[1], old[2]-1])
                bio.write(old)
                continue
            if cur[0] == 177:
                old = bytes([old[0]+1, old[1]+1, old[2]-1])
                bio.write(old)
                continue

            if cur[0] == 131:
                old = bytes([127,0,0])
                bio.write(old)
                continue
            if cur[0] == 132:
                old = bytes([0,127,0])
                bio.write(old)
                continue
            if cur[0] == 133:
                old = bytes([0,0,127])
                bio.write(old)
                continue
            if cur[0] == 135:
                old = bytes([255-old[0], 255-old[1], 255-old[2]])
                bio.write(old)
                continue
            bio.write(cur)
            old = cur

        if quality_y == 7:
            dividor = 2
        if quality_y == 6:
            dividor = 3
        if quality_y == 5:
            dividor = 4
        if quality_y == 4:
            dividor = 6
        if quality_y == 3:
            dividor = 8
        if quality_y == 2:
            dividor = 12
        if quality_y == 1:
            dividor = 16
        if quality_y == 0:
            dividor = 32

        
        if debug:
            print('CREATING OUTPUT IMAGE...')
        im = Image.frombytes(data=(numpy.array(list(bio.getvalue()), dtype=numpy.uint8)*dividor).tobytes(), size=(size_w,size_h), mode='RGB')

        # What I do here?
        # It's simple, when color compression is used, there is no white color, so I have to add Image some brightness
        # (128 color image = without black 127 colors, so maximum rounded color value is 254, not 256 ;) )
        enhancer = ImageEnhance.Brightness(im)
        im = enhancer.enhance(256/((256//dividor-1)*dividor))

        if image_mode == 1:
            if debug:
                print('PUTTING ALPHA...')
            im.putalpha(Image.frombytes(mode='L', data=(numpy.array(list(alpha), dtype=numpy.uint8)*2).tobytes(), size=(size_w,size_h)))

        enlarger = enlargers[_enlarger]
        if quality_x == 2:
            im = im.resize((im.size[0]*2, im.size[1]*2), enlarger)
        if quality_x == 1:
            im = im.resize((im.size[0]*4, im.size[1]*4), enlarger)
        if quality_x == 0:
            im = im.resize((im.size[0]*6, im.size[1]*6), enlarger)

    elif image_mode == 2:

        Y = data[:size_w*size_h]
        U = data[size_w*size_h:(size_w*size_h)*2]
        V = data[(size_w*size_h)*2:]
        Ya = numpy.array(list(Y), dtype=numpy.uint8)
        Ua = numpy.array(list(U), dtype=numpy.uint8)
        Va = numpy.array(list(V), dtype=numpy.uint8)
        imdata = numpy.ravel(numpy.column_stack(([Ya, Ua, Va])).tobytes())
        im = Image.frombytes(data=imdata, size=(size_w,size_h), mode='YCbCr')
        im = im.convert('RGB')

    elif image_mode == 3:

        enlarger = enlargers[_enlarger]
        dbio = BytesIO()
        dbio.write(data)
        dbio.seek(0)
        yBLOCK = dbio.read(((size_w//div_y)*(size_h//div_y)))
        uBLOCK = dbio.read(((size_w//div_u)*(size_h//div_u)))
        vBLOCK = dbio.read(((size_w//div_v)*(size_h//div_v)))
        dbio.close()
        del dbio
        y = numpy.array(list(yBLOCK),dtype=numpy.uint8)
        u = numpy.array(list(uBLOCK),dtype=numpy.uint8)
        v = numpy.array(list(vBLOCK),dtype=numpy.uint8)
        
        color_dividors = [36.0,17.0,12.0,8.0,4.0,2.0,1.340,1.143]
        cdiv = color_dividors[quality_y]
        
        u = (u*cdiv).astype(numpy.uint8)
        v = (v*cdiv).astype(numpy.uint8)
        y = (y*cdiv).astype(numpy.uint8)
        Y = Image.frombytes(data=y.tobytes(), mode='L', size=(size_w//div_y,size_h//div_y)).resize((size_w, size_h), enlarger)
        U = Image.frombytes(data=u.tobytes(), mode='L', size=(size_w//div_u,size_h//div_u)).resize((size_w, size_h), enlarger)
        V = Image.frombytes(data=v.tobytes(), mode='L', size=(size_w//div_v,size_h//div_v)).resize((size_w, size_h), enlarger)
        out = Image.merge('YCbCr', (Y,U,V))
        im = out.convert('RGB')

    elif image_mode == 4:
        
        y = numpy.array(list(data),dtype=numpy.uint8)
        
        color_dividors = [32.0,16.0,12.0,8.0,4.0,2.0,1.340,1.0]
        cdiv = color_dividors[quality_y]
        
        imdata = (y*cdiv).astype(numpy.uint8)
        size_h = size_h//size_w
        out = Image.frombytes(data=imdata.tobytes(), size=(size_w,size_h), mode='L')
        out = out.convert('RGB')
        enhancer = ImageEnhance.Brightness(out)
        im = enhancer.enhance(256/((256//cdiv-1)*cdiv))
        enlarger = enlargers[_enlarger]
        if quality_x == 2:
            im = im.resize((im.size[0]*2, im.size[1]*2), enlarger)
        if quality_x == 1:
            im = im.resize((im.size[0]*4, im.size[1]*4), enlarger)
        if quality_x == 0:
            im = im.resize((im.size[0]*6, im.size[1]*6), enlarger)

    elif image_mode == 5:

        size_h = size_h//size_w//3
        _prev_colors = [128, 64, 48, 32, 16, 12, 8, 4]
        im = Image.frombytes(data=(numpy.array(list(data),dtype=numpy.uint8)*_prev_colors[quality_y]).tobytes(), size=(size_w, size_h), mode='RGB')
        if quality_x == 3:
            im = im.resize((im.size[0]*2, im.size[1]*2), enlargers[_enlarger])
        elif quality_x == 2:
            im = im.resize((im.size[0]*8, im.size[1]*8), enlargers[_enlarger])
        elif quality_x == 1:
            im = im.resize((im.size[0]*16, im.size[1]*16), enlargers[_enlarger])
        elif quality_x == 0:
            im = im.resize((im.size[0]*64, im.size[1]*64), enlargers[_enlarger])
        enhancer = ImageEnhance.Brightness(im)
        im = enhancer.enhance(256/((256//_prev_colors[quality_y]-1)*_prev_colors[quality_y]))

    elif image_mode == 6:

        size_h = size_h//size_w//4
        Y = data[:size_w*size_h]
        U = data[size_w*size_h:(size_w*size_h)*2]
        V = data[(size_w*size_h)*2:(size_w*size_h)*3]
        A = data[(size_w*size_h)*3:]
        Ya = numpy.array(list(Y), dtype=numpy.uint8)
        Ua = numpy.array(list(U), dtype=numpy.uint8)
        Va = numpy.array(list(V), dtype=numpy.uint8)
        imdata = numpy.ravel(numpy.column_stack(([Ya, Ua, Va])).tobytes())
        im = Image.frombytes(data=imdata, size=(size_w,size_h), mode='YCbCr')
        im = im.convert('RGB')
        im.putalpha(Image.frombytes(data=A, size=(size_w,size_h), mode='L'))

    elif image_mode == 7:

        color_dividors = [36.0,17.0,12.0,8.0,4.0,2.0,1.340,1.143]
        im = Image.new('YCbCr', (size_w,size_h), (0,0,0))
        dbio = BytesIO()
        cdiv = color_dividors[quality_y]
        dbio.write((numpy.array(list(data[:datalen]), numpy.float16)*cdiv).astype(numpy.uint8))
        dbio.seek(0)
        hints = data[datalen:]
        del data

        cnt = 0
        reads = {3: 768, 2: 192, 1: 48, 0: 12}
        for x in range(0, size_h, 16):
            for y in range(0, size_w, 16):
                en = reads[hints[cnt]]
                data = dbio.read(en)
                if hints[cnt] == 3:
                    ndata = numpy.ravel(numpy.column_stack((numpy.array(list(data[:256]), numpy.uint8),numpy.array(list(data[256:512]), numpy.uint8),numpy.array(list(data[512:]), numpy.uint8))))
                    im.paste(Image.frombytes(data=ndata.tobytes(), mode='YCbCr', size=(16,16)), (y,x))
                    cnt += 1
                    continue
                if hints[cnt] == 2:
                    ndata = numpy.ravel(numpy.column_stack((numpy.array(list(data[:64]), numpy.uint8),numpy.array(list(data[64:128]), numpy.uint8),numpy.array(list(data[128:]), numpy.uint8))))
                    im.paste(Image.frombytes(data=ndata.tobytes(), mode='YCbCr', size=(8,8)).resize((16,16), Image.BILINEAR), (y,x))
                    cnt += 1
                    continue
                if hints[cnt] == 1:
                    ndata = numpy.ravel(numpy.column_stack((numpy.array(list(data[:16]), numpy.uint8),numpy.array(list(data[16:32]), numpy.uint8),numpy.array(list(data[32:]), numpy.uint8))))
                    im.paste(Image.frombytes(data=ndata.tobytes(), mode='YCbCr', size=(4,4)).resize((16,16), Image.BILINEAR), (y,x))
                    cnt += 1
                    continue
                ndata = numpy.ravel(numpy.column_stack((numpy.array(list(data[:4]), numpy.uint8),numpy.array(list(data[4:8]), numpy.uint8),numpy.array(list(data[8:]), numpy.uint8))))
                im.paste(Image.frombytes(data=ndata.tobytes(), mode='YCbCr', size=(2,2)).resize((16,16), Image.BILINEAR), (y,x))
                cnt += 1
        im = im.convert('RGB')


    if not quiet:
        print('Succesfully decompressed image in:', time.time()-told, 'seconds.')

    if outi == None and showonly:
        im.show()
    elif outi == None and not showonly:
        return im
    else:
        im.save(outi)
    return True


def identify(MAPFfile, debug=True):

    if debug:
        print('OPENING IMAGE...')

    if type(MAPFfile) != _io.BytesIO: 
        if not os.path.exists(MAPFfile):
            if __name__ == '__main__':
                print('MAPF ERROR:', errors[4])
                sys.exit(11)
            else:
                raise MAPFException(errors[4])
        f = open(MAPFfile, 'rb')
    else:
        f = MAPFfile
        f.seek(0)
        del MAPFfile
    imtype = f.read(2)
    if imtype not in (b'mA', b'MA', b'ma'):
        if __name__ == '__main__':
            print('MAPF ERROR:', errors[1])
            sys.exit(3)
        else:
            raise MAPFException(errors[1])

    if debug:
        print('READING METADATA...')

    if imtype == b'mA':
        release, compress_mode, image_mode = bitstruct.unpack('u3u3u2', f.read(1))
    elif imtype == b'ma':
        release, compress_mode, image_mode = bitstruct.unpack('u3u3u2', f.read(1))
        image_mode += 4
    else:
        release, compress_mode, _enlarger = bitstruct.unpack('u3u3u2', f.read(1))
        image_mode = 3
    if image_mode > 7:
        if __name__ == '__main__':
            print('MAPF ERROR:', errors[0])
            sys.exit(4)
        else:
            raise MAPFException(errors[0])
    if imtype == b'mA' or imtype == b'ma':
        quality_x, quality_y, _enlarger = bitstruct.unpack('u2u4u2', f.read(1))
    else:
        quality_z, quality_y = bitstruct.unpack('u4u4', f.read(1))
    size_w = struct.unpack('>H', f.read(2))[0]
    has_alpha = False
    if image_mode != 7:
        if imtype == b'mA':
            datalen = struct.unpack('>I', f.read(4))[0]
            quality_x_list = [6, 4, 2, 1]
            size_w = size_w*quality_x_list[quality_x]
            size_h = int((datalen*quality_x_list[quality_x])/size_w/3)
            size_h = size_h*quality_x_list[quality_x]
        else:
            size_h = struct.unpack('>I', f.read(4))[0]
            datalen = size_h*size_w*3
            if image_mode == 6:
                datalen = size_h
    else:
        size_h = struct.unpack('>H', f.read(2))[0]
        datalen = struct.unpack('>I', f.read(4))[0]

    if image_mode == 4:
        datalen = datalen//3
        quality_x_list = [6, 4, 2, 1]
        size_h = size_h//size_w
        size_w = size_w*quality_x_list[quality_x]
        size_h = size_h*quality_x_list[quality_x]
    if image_mode == 5:
        quality_x_list = [64, 16, 8, 2]
        size_h = size_h//size_w//3
        size_w = size_w*quality_x_list[quality_x]
        size_h = size_h*quality_x_list[quality_x]
    if image_mode == 6:
        size_h = size_h//size_w//4

    if image_mode in (1,6):
        has_alpha = True

    other = locals()
    if debug:
        print('\nMAPF FILE INFO:')

    mapfinfo = {'version': versions[release],
            'release': release,
            'image_mode': _image_modes_reversed[image_mode],
            'image_mode_index': image_mode,
            'compress_mode': _compress_modes_reversed[compress_mode],
            'compress_mode_index': compress_mode,
            'width': size_w,
            'height': size_h,
            'data_length': datalen,
            'header_length': f.tell(),
            'has_alpha': has_alpha}

    if 'quality_x' in other:
        mapfinfo['scallar_quality'] = quality_x
    if 'quality_y' in other:
        mapfinfo['color_quality'] = quality_y
    if 'quality_z' in other:
        mapfinfo['subsampling_quality'] = quality_y
    if '_enlarger' in other:
        s_enlargers = ['BICUBIC', 'BILINEAR', 'LANCZOS', 'NEAREST']
        mapfinfo['enlarger'] = s_enlargers[_enlarger]
        mapfinfo['enlarger_index'] = _enlarger
    if 'imtype' in other:
        mapfinfo['head'] = imtype

    return mapfinfo

def _identify(image_path):
    xi = identify(image_path)
    for xitem in xi.items():
        print(xitem[0]+': '+str(xitem[1]))

if not os.path.exists(relative_path('./bcm.exe')):
    print('MAPF WARNING: There is no BCM binary included in executable (or bcm.exe file is in diffrent folder).\nIf you haven\'t bcm binary, you can download it from https://github.com/encode84/bcm.\nIf bcm.exe will be in the same folder as your MAPF executable, you can compress and decompress MAPF in bcm format.\n')
if not os.path.exists(relative_path('./nz.exe')):
    print('MAPF WARNING: There is no NANOZIP binary included in executable (or nz.exe file is in diffrent folder).\nIf you haven\'t nanozip binary, you can download it from http://nanozip.ijat.my/.\nIf nz.exe will be in the same folder as your MAPF executable, you can compress and decompress MAPF in nz format.\n')

if __name__ == '__main__':

    if '--version' in sys.argv:
        print('Your MAPF version is {} and release is {}.'.format(version, release))
        sys.exit(0)

    if '--identify' in sys.argv:
        xarg = None
        for xarg in sys.argv:
            if xarg.endswith('.mapf'):
                break
        _identify(xarg)
        sys.exit(0)

    if '--compressions' in sys.argv:
        for xcomp in available_compressions.items():
            print(xcomp[0]+': '+str(xcomp[1]))
        sys.exit(0)

    dist_req = False

    if not '--read' in sys.argv and not '-r' in sys.argv:
        dist_req = True
    else:
        if '-v' in sys.argv or '--view-only' in sys.argv:
            pass
        else:
            dist_req = True

    req_input = True
    save_input = dist_input = ''

    if len(sys.argv) > 1:

        if sys.argv[1].lower().endswith('.mapf'):
            req_input = False
            dist_req = False
            dist_input = None
            save_input = sys.argv[1]
            if len(sys.argv) > 2:
                if sys.argv[2].endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.tiff', '.ico')):
                    dist_input = sys.argv[2]

    if len(sys.argv) > 1:

        if sys.argv[1].lower().endswith(('.png','.jpg','.jpeg','.bmp','.webp','.gif','.tiff','.ico')):
            req_input = False
            dist_req = False
            save_input = sys.argv[1]
            if len(sys.argv) > 2:
                if sys.argv[2].lower().endswith('.mapf'):
                    dist_input = sys.argv[2]
                else:
                    dist_input = sys.argv[1]+'.mapf'
            else:
                dist_input = sys.argv[1]+'.mapf'

    usage = '''
    Macro Advanced Image Format usage:
    Encode   [first way]  --> MAPF input.(jpg,jpeg,png,bmp,webp,gif,tiff,ico) output.mapf {args}
    Decode   [first way]  --> MAPF input.mapf output.(jpg,jpeg,png,bmp,webp,gif,tiff,icon) {args}
    Encode   [second way] --> MAPF input.(jpg,jpeg,png,bmp,webp,gif,tiff,ico) {args}
    Decode   [second way] --> MAPF input.mapf {args}
    Encode   [third way]  --> MAPF -i input.(jpg,jpeg,png,bmp,webp,gif,tiff,ico) -d input.mapf {args}
    Decode   [third way]  --> MAPF -i input.mapf -d file.(jpg,jpeg,png,bmp,webp,gif,tiff,icon) -r {args}
    Decode   [fourth way] --> MAPF -i input.mapf -r -v {args}
    Identify [first way]  --> MAPF input.mapf --identify

    Use --help to display args ;)'''

    if '--usage' in sys.argv:
        print(usage)
        sys.exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--usage', help='Displays usage examples and exit.', action='store_true')
    parser.add_argument('-r', '--read', help='Read image.', action='store_true')
    parser.add_argument('-i','--input', help='Input image.', required=req_input, type=str)
    parser.add_argument('-d','--destination', help='Destination of image.', default=None, required=dist_req)
    parser.add_argument('-nd', '--no-debug', help='Don\'t display debug info.', action='store_false')
    parser.add_argument('-nh', '--no-helper', help='Disable internal compression helper.', action='store_false')
    parser.add_argument('-hm','--helper-max', help='Set max data lenght for helper limit.', required=False, type=int, default=8)
    parser.add_argument('-v', '--view-only', help='View readed image without saving it on disk.', action='store_true')
    parser.add_argument('-cm','--compress-mode', help='Compression used in external comperssing (xz, bz2, nz, brotli, zstd, snappy, bcm, without).', required=False, type=str, default='xz')
    parser.add_argument('-cp','--compress-power', help='Power of compression.', required=False, type=int, default=9)
    parser.add_argument('-m','--image-mode', help='Mode of image.', required=False, default=3)
    parser.add_argument('-c','--color-quality', help='Color mode used in image (range 0-7, 0 is smaller size, 7 is maximum colors).', required=False, type=int, default=6)
    parser.add_argument('-y','--yuv-quality', help='YUV subsampling quality (range 0-15, 0 is smaller size, 15 best).', required=False, type=int, default=4)
    parser.add_argument('-s','--scalar-quality', help='Image will be resized to smaller size in saving and enlarged in reading (range 0-3, 0 is smaller size, 3 is original image size).', required=False, type=int, default=3)
    parser.add_argument('-e','--enlarger', help='Enlarger used in image (0 is BICUBIC, 1 is BILINEAR, 2 is LANCZOS, 3 is NEAREST-NEIGHTBOUR).', required=False, type=int, default=2)
    parser.add_argument('-o','--optimizer', help='Enable optimizer.', action='store_true')
    parser.add_argument('-q','--quality', help='Auto-calculated quality for image (In all lossy modes range 0-31, in mode 3 and 7 range 0-127... less is smaller file size) [default, -1].', required=False, type=int, default=-1)
    parser.add_argument('-om','--optimizer-maxdiff', help='Optimizer maximum pixels difference.', required=False, type=int, default=25)
    parser.add_argument('-oc','--optimizer-chunk', help='Optimizer pixels chunk size.', required=False, type=int, default=8)
    parser.add_argument('-bq','--quiet', help='Locks ANY print to stdout.', action='store_true')
    args, unknown = parser.parse_known_args()
    args = vars(args)
    if sys.argv[1].lower().endswith('.mapf'):
        args['read'] = True
        if len(sys.argv) > 2:
            if sys.argv[2].endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.tiff', '.ico')):
                args['view_only'] = False
            else:
                args['view_only'] = True
        else:
            args['view_only'] = True

    if not req_input and not dist_req:
        args['input'] = save_input
        args['destination'] = dist_input

    if type(args['image_mode']) == str:
        try:
            args['image_mode'] = image_modes[args['image_mode'].upper()]
        except:
            pass

    try:
        if args['read']:
            read(args['input'], args['destination'], args['view_only'], args['no_debug'], args['quiet'])
        else:
            save(args['input'], args['destination'], int(args['image_mode']), args['scalar_quality'], args['color_quality'], args['yuv_quality'], args['quality'], args['compress_mode'], args['compress_power'], args['enlarger'], args['optimizer'], args['optimizer_chunk'], args['optimizer_maxdiff'], args['no_helper'], args['helper_max'], args['no_debug'], args['quiet'], False)
    except Exception as e:
        print('MAPF RELEASE: '+str(release)+'\n'+'SYSTEM ERROR: ')
        traceback.print_exc()
        print('\nMAPF FATAL ERROR: Failed to start image processing, cause catched internal python error.\nCheck your args line or write me on github (github.com/olokelo), including error info above :D')
        sys.exit(-1)

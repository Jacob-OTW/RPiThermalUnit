import time
import numpy as np
import os
import cv2
import sys
from menu import Camera
from color_pallets import BHOT, WHOT, P45, PSQ, COTI

def c_to_k(c_temp):
    return 64 * (c_temp + 273.15)


def k_to_c(k_temp):
    return k_temp / 64 - 273.15

def overlay_image(dst, src):
    dst[:src.shape[0], :src.shape[1]] = src

def fit_rect_all(small: tuple[int, int], big: tuple[int, int]) -> tuple[int, int]:
    multi = max(small[0] / big[0], small[1] / big[1])

    return int(small[0] / multi), int(small[1] / multi)


def fast_scale(dst, src, offset, scale, target_size):
    """
    Used for shifting and scaling the camera image
    """
    height, width, *_ = src.shape
    target_width, target_height = target_size
    offset_x, offset_y = int(offset[0]), int(offset[1])
    scaled_width, scaled_height = int(width / scale), int(height / scale)
    scaled_half_width, scaled_half_height = int(scaled_width / 2), int(scaled_height / 2)
    centre_x, centre_y = int(width / 2), int(height / 2)

    start_y = centre_y - scaled_half_height + offset_y
    start_x = centre_x - scaled_half_width + offset_x

    clamped = lambda v, m: min(m, max(0, v))
    real_start_y = clamped(start_y, height - scaled_height)
    real_start_x = clamped(start_x, width - scaled_width)

    dif_y, dif_x = start_y - real_start_y, start_x - real_start_x

    sized = cv2.resize(
                        src[real_start_y:real_start_y + scaled_height, real_start_x:real_start_x + scaled_width]
                       , fit_rect_all((scaled_width, scaled_height), (target_width, target_height)), interpolation=cv2.INTER_NEAREST)
    sized_height, sized_width, *_ = sized.shape
    sized_chopped = sized[max(0, dif_y):sized_height + dif_y:, max(0, dif_x):sized_width + dif_x]
    sized_height, sized_width, *_ = sized_chopped.shape

    base_start_y = int(target_height / 2) - int(sized_height / 2) - dif_y
    base_start_x = int(target_width / 2) - int(sized_width / 2) - dif_x

    real_base_start_y = clamped(base_start_y, target_height - sized_height)
    real_base_start_x = clamped(base_start_x, target_width - sized_width)

    dst[real_base_start_y:real_base_start_y + sized_height, real_base_start_x:real_base_start_x + sized_width] = sized_chopped

def main():
    os.system("TERM=linux setterm -foreground black -clear all >/dev/tty0") # Stops terminal cursor blinking

    with open(f"/sys/class/graphics/fb0/virtual_size", "r") as file:
        wh = file.read()
        wa, ha = wh.split(',')
        w = int(wa)
        h = int(ha)
        print(w, "x", h)

    with open(f"/sys/class/graphics/fb0/bits_per_pixel", "r") as file:
        bpp = int(file.read())
        if bpp != 16:
            print("BPP is not 16bit")
            sys.exit(-1)

    buf = np.memmap('/dev/fb0', dtype='uint16', mode='w+', shape=(h, w))
    buf[:] = 0xffff

    circle = np.zeros((h, w, 3)).astype(np.uint8)
    cv2.circle(circle, (int(circle.shape[1] / 2), int(circle.shape[0] / 2)), int(circle.shape[0] / 2), (255, 255, 255), cv2.FILLED)

    cam = Camera((w, h))

    disable_cursor_flag = True

    cap = cv2.VideoCapture(-1)
    cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)

    base = np.zeros((h, w, 3)).astype(np.uint8)
    bgr = np.zeros((192, 256, 3)).astype(np.uint8)

    start_time = time.time()
    try:
        t = time.time()
        while True:
            mils = time.time() - t
            t = time.time()
            if mils > 0:
                cam.fps = 1 / mils

            result, video_frame = cap.read()


            if not result:
                continue

            if disable_cursor_flag and time.time() - start_time > 1: # If this file in run directly on boot, sometimes it's faster than the processing starting the cursor, so it needs to be disabled again
                disable_cursor_flag = False
                os.system("TERM=linux setterm -foreground black -clear all >/dev/tty0")

            white_hot_gray = cv2.cvtColor(np.reshape(video_frame.view(np.uint16), (192, 256, 1)).view(np.uint8), cv2.COLOR_YUV2GRAY_YUYV)

            match cam.store["color"].value:
                case "WHOT":
                    WHOT[:, :] = cv2.cvtColor(white_hot_gray, cv2.COLOR_GRAY2RGB)
                case "BHOT":
                    BHOT[:, :] = BHOT[white_hot_gray]
                case "PSQ":
                    PSQ[:, :] = PSQ[white_hot_gray]

            base[:, :] = 0x00

            fast_scale(base, bgr, (cam.store["x_offset"].value, cam.store["y_offset"].value),
                          cam.store["scale"].value, (w, h))

            if cam.selected_menu is not None:
                overlay_image(base, cv2.flip(cam.menu_image(), 1))

            pic16 = cv2.cvtColor(base, cv2.COLOR_RGB2BGR565).view(dtype=np.uint16)

            buf[:pic16.shape[0], :pic16.shape[1]] = pic16.squeeze()


    except KeyboardInterrupt:
        pass
    finally:
        os.system("TERM=linux setterm -foreground white -clear all >/dev/tty0")


if __name__ == '__main__':
    main()
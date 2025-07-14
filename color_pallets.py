import numpy as np

P45 = np.zeros((256, 3)).astype(np.uint8)
for i in range(256):
    """red = 1.0218971487**i
    blue = -0.05 * (i - 50) ** 2 + 70
    green = i / 2 - red"""
    red = 1.0218971487 ** i
    blue = i - red
    green = i - red

    P45[i] = [min(255, max(0, red)), min(255, max(0, green)), min(255, max(0, blue))]

WHOT = np.zeros((256, 3)).astype(np.uint8)
for i in range(256):
    red = i
    blue = i
    green = i

    WHOT[i] = [min(255, max(0, red)), min(255, max(0, green)), min(255, max(0, blue))]

BHOT = np.zeros((256, 3)).astype(np.uint8)
for i in range(256):
    red = 255 - i
    blue = 255 - i
    green = 255 - i

    BHOT[i] = [min(255, max(0, red)), min(255, max(0, green)), min(255, max(0, blue))]

PSQ = np.zeros((256, 3)).astype(np.uint8)
for i in range(256):
    curve = ((i / 255)**2) * 255
    red = curve * (250 / 255)
    green = curve * (156 / 255)
    blue = curve * (28 / 255)

    PSQ[i] = [min(255, max(0, red)), min(255, max(0, green)), min(255, max(0, blue))]

COTI = np.zeros((256, 3)).astype(np.uint8)
for i in range(256):
    red = (i / 255) * 35
    green = 0
    blue = 0

    COTI[i] = [min(255, max(0, red)), min(255, max(0, green)), min(255, max(0, blue))]

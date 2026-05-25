VALID_FIRMWARE_PATTERN = r"GF5288_HTSEC_APP_100(11|20)"

PSK = bytes.fromhex(
    "0000000000000000000000000000000000000000000000000000000000000000")

PSK_WHITE_BOX = bytes.fromhex(
    "ec35ae3abb45ed3f12c4751f1e5c2cc05b3c5452e9104d9f2a3118644f37a04b"
    "6fd66b1d97cf80f1345f76c84f03ff30bb51bf308f2a9875c41e6592cd2a2f9e"
    "60809b17b5316037b69bb2fa5d4c8ac31edb3394046ec06bbdacc57da6a756c5")

SENSOR_WIDTH = 108
SENSOR_HEIGHT = 88
USB_VENDOR = 0x27C6
USB_PRODUCT = 0x5385

OTP_HASH_TABLE = bytes.fromhex(
    "00 07 0e 09 1c 1b 12 15 38 3f 36 31 24 23 2a 2d"
    "70 77 7e 79 6c 6b 62 65 48 4f 46 41 54 53 5a 5d"
    "e0 e7 ee e9 fc fb f2 f5 d8 df d6 d1 c4 c3 ca cd"
    "90 97 9e 99 8c 8b 82 85 a8 af a6 a1 b4 b3 ba bd"
    "c7 c0 c9 ce db dc d5 d2 ff f8 f1 f6 e3 e4 ed ea"
    "b7 b0 b9 be ab ac a5 a2 8f 88 81 86 93 94 9d 9a"
    "27 20 29 2e 3b 3c 35 32 1f 18 11 16 03 04 0d 0a"
    "57 50 59 5e 4b 4c 45 42 6f 68 61 66 73 74 7d 7a"
    "89 8e 87 80 95 92 9b 9c b1 b6 bf b8 ad aa a3 a4"
    "f9 fe f7 f0 e5 e2 eb ec c1 c6 cf c8 dd da d3 d4"
    "69 6e 67 60 75 72 7b 7c 51 56 5f 58 4d 4a 43 44"
    "19 1e 17 10 05 02 0b 0c 21 26 2f 28 3d 3a 33 34"
    "4e 49 40 47 52 55 5c 5b 76 71 78 7f 6a 6d 64 63"
    "3e 39 30 37 22 25 2c 2b 06 01 08 0f 1a 1d 14 13"
    "ae a9 a0 a7 b2 b5 bc bb 96 91 98 9f 8a 8d 84 83"
    "de d9 d0 d7 c2 c5 cc cb e6 e1 e8 ef fa fd f4 f3")

DEFAULT_CONFIG = bytes.fromhex(
    "40 11 6c 7d 28 a5 28 cd 1c e9 10 f9 00 f9 00 f9"
    "00 04 02 00 00 08 00 11 11 ba 00 01 80 ca 00 07"
    "00 84 00 be b2 86 00 c5 b9 88 00 b5 ad 8a 00 9d"
    "95 8c 00 00 be 8e 00 00 c5 90 00 00 b5 92 00 00"
    "9d 94 00 00 af 96 00 00 bf 98 00 00 b6 9a 00 00"
    "a7 30 00 6c 1c 50 00 01 05 d0 00 00 00 70 00 00"
    "00 72 00 78 56 74 00 34 12 26 00 00 12 20 00 10"
    "40 12 00 03 04 02 02 16 21 2c 02 0a 03 2a 01 02"
    "00 22 00 01 20 24 00 32 00 80 00 05 04 5c 00 00"
    "01 56 00 28 20 58 00 01 00 32 00 24 02 82 00 80"
    "0c 20 02 88 0d 2a 01 92 07 22 00 01 20 24 00 14"
    "00 80 00 05 04 5c 00 00 01 56 00 08 20 58 00 03"
    "00 32 00 08 04 82 00 80 0c 20 02 88 0d 2a 01 18"
    "04 5c 00 80 00 54 00 00 01 62 00 09 03 64 00 18"
    "00 82 00 80 0c 20 02 88 0d 2a 01 18 04 5c 00 80"
    "00 52 00 08 00 54 00 00 01 00 00 00 00 00 61 4f")

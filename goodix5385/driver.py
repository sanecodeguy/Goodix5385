import dataclasses
import logging
import os
import re
import time

import Crypto.Hash.SHA256

from . import protocol
from . import tool
from . import wrapless
from . import config

FDT_BASE_LEN = 24
HV_VALUE = 6
TCODE_TAG = 0x5C
DAC_L_TAG = 0x220
DELTA_DOWN_TAG = 0x82


@dataclasses.dataclass
class CalibrationParams:
    tcode: int
    delta_fdt: int
    delta_down: int
    delta_up: int
    delta_img: int
    delta_nav: int
    dac_h: int
    dac_l: int
    dac_delta: int
    fdt_base_down: bytes
    fdt_base_up: bytes
    fdt_base_manual: bytes
    calib_image: list[int] | None

    def update_fdt_bases(self, fdt_base: bytes):
        assert len(fdt_base) == FDT_BASE_LEN
        self.fdt_base_down = fdt_base[:]
        self.fdt_base_up = fdt_base[:]
        self.fdt_base_manual = fdt_base[:]


def is_valid_psk(device: wrapless.Device):
    psk_hash = device.read_psk_hash()
    return psk_hash == Crypto.Hash.SHA256.SHA256Hash(config.PSK).digest()


def write_psk(device: wrapless.Device):
    print("Writing white-box all-zero PSK")
    device.write_psk_white_box(config.PSK_WHITE_BOX)

    if not is_valid_psk(device):
        raise Exception("Could not set all-zero PSK")


def device_enable(device: wrapless.Device):
    device.reset(0, False)
    time.sleep(0.01)

    reg_data = device.read_data(0, 4, 0.2)
    chip_id = wrapless.decode_u32(reg_data)
    if chip_id >> 8 != 0x220C:
        raise Exception(f"Unsupported chip ID: {chip_id}")

    print(f"Chip ID: {chip_id:#x}")


def compute_otp_hash(data):
    checksum = 0
    for byte in data:
        checksum = config.OTP_HASH_TABLE[checksum ^ byte]
    return ~checksum & 0xFF


def verify_otp_hash(otp):
    data = otp[:25] + otp[26:]
    received_hash = otp[25]
    computed_hash = compute_otp_hash(data)

    if received_hash == computed_hash:
        print("Valid OTP")
    else:
        raise Exception(f"OTP hash incorrect: {received_hash} != {computed_hash}")


def check_sensor(device: wrapless.Device):
    otp = device.read_otp(0.2)
    print(f"OTP: {otp.hex(' ')}")

    verify_otp_hash(otp)

    diff = otp[17] >> 1 & 0x1F
    print(f"[0x11]:{otp[0x11]:#x}, diff[5:1]={diff:#x}")

    tcode = otp[23] + 1 if otp[23] != 0 else 0

    if diff == 0:
        delta_fdt = 0
        delta_down = 0xD
        delta_up = 0xB
        delta_img = 0xC8
        delta_nav = 0x28
    else:
        tmp = diff + 5
        tmp2 = (tmp * 0x32) >> 4

        delta_fdt = tmp2 // 5
        delta_down = tmp2 // 3
        delta_up = delta_down - 2
        delta_img = 0xC8
        delta_nav = tmp * 4

    if otp[17] == 0 or otp[22] == 0 or otp[31] == 0:
        dac_h = 0x97
        dac_l = 0xD0
    else:
        dac_h = (otp[17] << 8 ^ otp[22]) & 0x1FF
        dac_l = (otp[17] & 0x40) << 2 ^ otp[31]

    print(f"tcode:{hex(tcode)} delta down:{hex(delta_down)} "
          f"delta up:{hex(delta_up)} delta img:{hex(delta_img)} "
          f"delta nav:{hex(delta_nav)} dac_h:{hex(dac_h)} dac_l:{hex(dac_l)}")

    dac_delta = 0xC83 // tcode
    print(f"sensor broken dac_delta={dac_delta}")

    fdt_base = b"\x00" * FDT_BASE_LEN
    return CalibrationParams(
        tcode, delta_fdt, delta_down, delta_up, delta_img, delta_nav,
        dac_h, dac_l, dac_delta,
        fdt_base[:], fdt_base[:], fdt_base[:], None,
    )


def fix_config_checksum(config_data):
    checksum = 0xA5A5
    for short_idx in range(0, len(config_data) - 2, 2):
        short = int.from_bytes(config_data[short_idx:short_idx + 2], byteorder="little")
        checksum += short
        checksum &= 0xFFFF
    checksum = 0x10000 - checksum
    checksum_bytes = checksum.to_bytes(length=2, byteorder="little")
    config_data[-2] = checksum_bytes[0]
    config_data[-1] = checksum_bytes[1]


def replace_value_in_section(config_data, section_num, tag, value):
    value_bytes = int.to_bytes(value, length=2, byteorder="little")

    section_table = config_data[1:0x11]
    section_base = section_table[section_num * 2]
    section_size = section_table[section_num * 2 + 1]

    for entry_base in range(section_base, section_base + section_size, 4):
        entry_tag = int.from_bytes(config_data[entry_base:entry_base + 2],
                                   byteorder="little")
        if entry_tag == tag:
            config_data[entry_base + 2] = value_bytes[0]
            config_data[entry_base + 3] = value_bytes[1]


def upload_config(device: wrapless.Device, calib_params: CalibrationParams):
    chip_config = bytearray(config.DEFAULT_CONFIG)
    replace_value_in_section(chip_config, 2, TCODE_TAG, calib_params.tcode)
    replace_value_in_section(chip_config, 3, TCODE_TAG, calib_params.tcode)
    replace_value_in_section(chip_config, 4, TCODE_TAG, calib_params.tcode)
    replace_value_in_section(chip_config, 2, DAC_L_TAG, calib_params.dac_l << 4 | 8)
    replace_value_in_section(chip_config, 3, DAC_L_TAG, calib_params.dac_l << 4 | 8)
    replace_value_in_section(chip_config, 2, DELTA_DOWN_TAG, calib_params.delta_down << 8 | 0x80)
    fix_config_checksum(chip_config)

    device.upload_config(chip_config, 0.5)


def get_fdt_base_with_tx(device: wrapless.Device, tx_enable: bool, calib_params: CalibrationParams):
    op_code = 0xD
    if not tx_enable:
        op_code |= 0x80

    payload = op_code.to_bytes(length=1, byteorder="little")
    payload += calib_params.fdt_base_manual
    fdt_base = device.execute_fdt_operation(
        wrapless.FingerDetectionOperation.MANUAL, payload, 0.5)
    assert fdt_base is not None
    return fdt_base


def get_image(device: wrapless.Device, tx_enable: bool, hv_enable: bool,
              use_dac: str, is_finger: bool, calib_params: CalibrationParams):
    if tx_enable:
        op_code = 0x1
    else:
        op_code = 0x81

    if is_finger:
        op_code |= 0x40

    if hv_enable:
        hv_value = HV_VALUE
    else:
        hv_value = 0x10

    if use_dac == "h":
        dac = calib_params.dac_h
    elif use_dac == "l":
        dac = calib_params.dac_l
    else:
        raise Exception("Invalid DAC type")

    request = op_code.to_bytes(length=1, byteorder="little")
    request += hv_value.to_bytes(length=1, byteorder="little")
    request += dac.to_bytes(length=2, byteorder="little")

    return tool.decode_image(device.get_image(request, 0.5))


def is_fdt_base_valid(fdt_data_1: bytes, fdt_data_2: bytes, max_delta: int):
    assert len(fdt_data_1) == len(fdt_data_2)
    logging.debug(f"Checking FDT data, max delta: {max_delta}")
    for idx in range(0, len(fdt_data_1), 2):
        fdt_val_1 = int.from_bytes(fdt_data_1[idx:idx + 2], byteorder="little")
        fdt_val_2 = int.from_bytes(fdt_data_2[idx:idx + 2], byteorder="little")

        delta = abs((fdt_val_2 >> 1) - (fdt_val_1 >> 1))
        if delta > max_delta:
            return False
    return True


def validate_base_img(base_image_1: list[int], base_image_2: list[int], image_threshold: int):
    assert len(base_image_1) == config.SENSOR_WIDTH * config.SENSOR_HEIGHT
    assert len(base_image_2) == config.SENSOR_WIDTH * config.SENSOR_HEIGHT

    diff_sum = 0
    for row_idx in range(2, config.SENSOR_HEIGHT - 2):
        for col_idx in range(2, config.SENSOR_WIDTH - 2):
            offset = row_idx * config.SENSOR_WIDTH + col_idx
            image_val_1 = base_image_1[offset]
            image_val_2 = base_image_2[offset]
            diff_sum += abs(image_val_2 - image_val_1)

    avg = diff_sum / ((config.SENSOR_HEIGHT - 4) * (config.SENSOR_WIDTH - 4))
    logging.debug(f"Checking image data, avg: {avg:.2f}, threshold: {image_threshold}")
    if avg > image_threshold:
        raise Exception("Invalid base image")


def generate_fdt_base(fdt_data: bytes):
    fdt_base = b""
    for idx in range(0, len(fdt_data), 2):
        fdt_val = int.from_bytes(fdt_data[idx:idx + 2], byteorder="little")
        fdt_base_val = (fdt_val & 0xFFFE) * 0x80 | fdt_val >> 1
        fdt_base += fdt_base_val.to_bytes(length=2, byteorder="little")
    return fdt_base


def update_all_base(device: wrapless.Device, calib_params: CalibrationParams):
    upload_config(device, calib_params)

    fdt_data_tx_enabled = get_fdt_base_with_tx(device, True, calib_params)
    image_tx_enabled = get_image(device, True, True, "l", False, calib_params)
    fdt_data_tx_disabled = get_fdt_base_with_tx(device, False, calib_params)

    fdt_base_valid = is_fdt_base_valid(fdt_data_tx_enabled, fdt_data_tx_disabled, calib_params.delta_fdt)
    if not fdt_base_valid:
        raise Exception("Invalid FDT")

    image_tx_disabled = get_image(device, False, True, "l", False, calib_params)

    validate_base_img(image_tx_enabled, image_tx_disabled, calib_params.delta_img)

    fdt_data_tx_enabled_2 = get_fdt_base_with_tx(device, True, calib_params)

    fdt_base_valid = is_fdt_base_valid(fdt_data_tx_enabled_2, fdt_data_tx_disabled, calib_params.delta_fdt)
    if not fdt_base_valid:
        raise Exception("Invalid FDT")

    calib_params.update_fdt_bases(generate_fdt_base(fdt_data_tx_enabled))
    calib_params.calib_image = image_tx_enabled

    print(f"FDT manual base: {calib_params.fdt_base_manual.hex(' ', 2)}")
    print("Decoding and saving calibration image")
    tool.write_pgm(calib_params.calib_image, config.SENSOR_HEIGHT, config.SENSOR_WIDTH, "clear.pgm")


def device_init(device: wrapless.Device):
    device.ping()

    firmware_version = device.read_firmware_version()
    print(f"Firmware version: {firmware_version}")
    if re.fullmatch(config.VALID_FIRMWARE_PATTERN, firmware_version) is None:
        raise Exception("Chip does not have a valid firmware")

    device_enable(device)

    print("Checking sensor")
    calib_params = check_sensor(device)
    print("Sensor check successful")

    print("Checking PSK hash")
    if not is_valid_psk(device):
        print("Updating PSK")
        write_psk(device)
    print("All-zero PSK set up")

    print("Establishing GTLS connection")
    device.establish_gtls_connection(config.PSK)
    print("Connection successfully established")

    print("Updating all base")
    update_all_base(device, calib_params)
    print("Update completed")

    print("Set to sleep mode")
    device.set_sleep_mode(0.2)

    return calib_params


def generate_fdt_up_base(fdt_data, touch_flag, calib_params: CalibrationParams):
    fdt_vals = []
    for idx in range(0, len(fdt_data), 2):
        fdt_val = int.from_bytes(fdt_data[idx:idx + 2], byteorder="little")
        fdt_vals.append(fdt_val)

    fdt_base_up_vals = []
    for fdt_val in fdt_vals:
        val = (fdt_val >> 1) + calib_params.delta_down
        fdt_base_up_vals.append(val * 0x100 | val)

    for idx in range(0xC):
        if ((touch_flag >> idx) & 1) == 0:
            fdt_base_up_vals[idx] = (calib_params.delta_up * 0x100 | calib_params.delta_up)

    fdt_base_up = b""
    for fdt_val in fdt_base_up_vals:
        fdt_base_up += fdt_val.to_bytes(2, "little")

    return fdt_base_up


def wait_for_finger_down(device: wrapless.Device, calib_params: CalibrationParams):
    fdt_data, touch_flag = device.wait_for_fdt_event(wrapless.FingerDetectionOperation.DOWN)
    calib_params.fdt_base_up = generate_fdt_up_base(fdt_data, touch_flag, calib_params)
    return fdt_data


def wait_for_finger_up(device: wrapless.Device, calib_params: CalibrationParams):
    fdt_data, _ = device.wait_for_fdt_event(wrapless.FingerDetectionOperation.UP)
    calib_params.fdt_base_down = generate_fdt_base(fdt_data)
    return fdt_data


def capture_fingerprint(device: wrapless.Device, calib_params: CalibrationParams, output_path: str = "raw_finger.pgm"):
    print("Powering on sensor")
    device.ec_control("on", 0.2)

    print("Setting up finger down detection")
    device.execute_fdt_operation(wrapless.FingerDetectionOperation.DOWN,
                                 calib_params.fdt_base_down, 0.5)

    print("Waiting for finger down")
    event_fdt_data = wait_for_finger_down(device, calib_params)

    manual_fdt_data = get_fdt_base_with_tx(device, False, calib_params)
    fdt_base_valid = is_fdt_base_valid(event_fdt_data, manual_fdt_data, calib_params.delta_fdt)
    if fdt_base_valid:
        raise Exception("Temperature event")

    print("Reading finger image")
    finger_image = get_image(device, True, True, "h", True, calib_params)
    tool.write_pgm(finger_image, config.SENSOR_HEIGHT, config.SENSOR_WIDTH, output_path)

    print("Setting up finger up detection")
    device.execute_fdt_operation(wrapless.FingerDetectionOperation.UP,
                                 calib_params.fdt_base_up, 0.5)

    print("Waiting for finger up")
    wait_for_finger_up(device, calib_params)

    print("Set to sleep mode")
    device.set_sleep_mode(0.2)

    print("Powering off sensor")
    time.sleep(0.5)
    device.ec_control("off", 0.2)

    return output_path


def initialize_device():
    if "DEBUG" in os.environ:
        logging.basicConfig(level=logging.DEBUG)

    device = wrapless.Device(config.USB_PRODUCT, protocol.USBProtocol)
    calib_params = device_init(device)

    return device, calib_params

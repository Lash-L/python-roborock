import pyshark

from roborock.roborock_message import RoborockParser, RoborockMessage

WIRESHARK_CAPTURE_PATH = ""
local_ip = ""
local_key = ""
capture = pyshark.FileCapture(WIRESHARK_CAPTURE_PATH, 'rb')
for packet in capture:
    if hasattr(packet, "ip"):
        if packet.ip.dst == local_ip or packet.ip.src ==local_ip:
            if hasattr(packet, "DATA"):
                if hasattr(packet.DATA, "data"):
                    try:
                        f = RoborockParser.decode(
                            bytes.fromhex(
                                packet.DATA.data),
                            local_key)
                    except Exception:
                        continue
                    if f and f[0] and f[0][0] and isinstance(f[0][0], RoborockMessage):
                        print(f)

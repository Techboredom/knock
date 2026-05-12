#!/usr/bin/env python3
"""
Computer_Waker - WoL Packet Test Script
=======================================
Simple utility to test Wake-On-LAN magic packet generation
and validate various MAC address formats.
"""

import sys


def validate_mac(mac):
    """Validate MAC address format."""
    if not mac or len(mac) < 5:
        return False

    # Clean MAC (remove colons, hyphens)
    clean = "".join(c for c in mac if c.isalnum())

    # Must be exactly 12 hex characters after cleaning
    if len(clean) < 12 or len(clean) > 12:
        return False

    # Verify all characters are hex
    try:
        int(clean, 16)
        return True
    except ValueError:
        return False


def generate_wol_packet(mac):
    """Generate a standard WoL magic packet."""
    if not validate_mac(mac):
        return None

    # Clean the MAC
    clean = "".join(c for c in mac if c.isalnum())
    mac_clean = clean[:12]  # Take first 12 if longer

    # Extract first 6 bytes (OUI)
    bytes_list = []
    try:
        for i in range(0, 12, 2):
            byte_val = int(mac_clean[i : i + 2], 16)
            bytes_list.append(byte_val)
    except ValueError:
        return None

    oui = bytes(bytes_list[:6])

    # Build packet: FF FE + OUI x 6
    packet = bytearray()
    packet.append(0xFF)  # Sync byte (1 byte)
    packet.append(0xFE)  # Header (1 byte)
    packet.extend(oui)  # First OUI (6 bytes)
    for _ in range(5):  # 5 more OUI copies (30 bytes)
        packet.extend(oui)

    return bytes(packet)


def format_hex(packet):
    """Format bytes as hex string with spaces and colons."""
    if not packet:
        return ""
    return " ".join(f"{b:02x}" for b in packet)


def format_hex_colon(packet):
    """Format bytes as colon-separated hex."""
    if not packet:
        return ""
    return ":".join(f"{b:02x}" for b in packet)


def print_packet_details(name, packet):
    """Print detailed packet information."""
    if not packet:
        return

    print(f"\n{'=' * 60}")
    print(f"Package name: {name}")
    print(f"Total length: {len(packet)} bytes")
    print(f"Hex with spaces: {format_hex(packet)}")
    print(f"Hex with colons: {format_hex_colon(packet)}")
    print(f"\nByte breakdown:")
    print(f"  Byte 0:  0x{packet[0]:02x} (sync)")
    print(f"  Byte 1:  0x{packet[1]:02x} (header)")
    bytes_str = [f"0x{b:02x}" for b in packet[2:]]
    for i, b in enumerate(bytes_str):
        print(f"  Byte {3 + i}:  {b}")
    print("=" * 60 + "\n")


def main():
    print("\n" + "=" * 60)
    print("Computer_Waker - WoL Magic Packet Test")
    print("=" * 60)
    print()

    # Test cases
    test_macs = [
        "00:11:22:33:44:55",
        "00-11-22-33-44-55",
        "001122334455",
        "AA:BB:CC:DD:EE:FF",
        "10:00:00:00:00:00",
    ]

    print("Validating MAC addresses...")
    print("-" * 60)
    for mac in test_macs:
        if validate_mac(mac):
            print(f"  ✓ Valid: {mac}")
        else:
            print(f"  ✗ Invalid: {mac}")

    print("\nGenerating WoL packets...")
    print("-" * 60)

    for mac in test_macs:
        if validate_mac(mac):
            packet = generate_wol_packet(mac)
            if packet:
                print_packet_details(mac, packet)
            else:
                print(f"  ✗ Failed to generate packet for {mac}")
        else:
            print(f"  - Skipped: {mac} (invalid MAC)")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

    # Info for sending
    print("\nInfo: To send a WoL packet:")
    print("  1. Configure sudo: sudo -n true")
    print("  2. Run: python3 wol_server.py")
    print("  3. Or send manually: python3 test_wol.py")
    print("\nOr use:")
    print("  sudo ifconfig -i eth0 etherwake - -")


if __name__ == "__main__":
    main()

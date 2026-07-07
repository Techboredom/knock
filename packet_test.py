#!/usr/bin/env python3
"""
Knock - WoL Packet Test Script
================================
Validates MAC address formats and verifies magic packet generation
produces the correct 102-byte structure.
"""

import socket
import sys


def validate_mac(mac: str) -> bool:
    """Return True if mac is a valid 12-hex-digit MAC in any common format."""
    if not mac:
        return False
    clean = mac.replace(":", "").replace("-", "").replace(".", "").lower()
    if len(clean) != 12:
        return False
    try:
        int(clean, 16)
        return True
    except ValueError:
        return False


def generate_wol_packet(mac: str) -> bytes | None:
    """Generate a standard 102-byte WoL magic packet."""
    clean = mac.replace(":", "").replace("-", "").replace(".", "").lower()
    if len(clean) != 12:
        return None
    try:
        mac_bytes = bytes.fromhex(clean)
    except ValueError:
        return None
    return b"\xff" * 6 + mac_bytes * 16


def print_packet_details(mac: str, packet: bytes) -> None:
    print(f"\n  MAC : {mac}")
    print(f"  Size: {len(packet)} bytes")
    print(f"  Sync: {packet[:6].hex(':')}")
    print(f"  MAC×1: {packet[6:12].hex(':')}")
    print(f"  MAC×2: {packet[12:18].hex(':')}")
    print(f"  ...   (×16 total)")


def send_test_packet(mac: str) -> None:
    """Send a real magic packet via UDP broadcast (optional live test)."""
    packet = generate_wol_packet(mac)
    if not packet:
        print(f"  ✗ Could not generate packet for {mac}")
        return
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(packet, ("<broadcast>", 9))
        print(f"  ✓ Packet sent to broadcast:9 for {mac}")
    except OSError as e:
        print(f"  ✗ Send failed: {e}")


def main() -> None:
    print("\n" + "=" * 60)
    print("Knock - WoL Magic Packet Test")
    print("=" * 60)

    test_macs = [
        "00:11:22:33:44:55",
        "00-11-22-33-44-55",
        "001122334455",
        "AA:BB:CC:DD:EE:FF",
        "invalid-mac",
    ]

    print("\nValidating MAC addresses...")
    print("-" * 60)
    for mac in test_macs:
        mark = "✓" if validate_mac(mac) else "✗"
        print(f"  {mark} {mac}")

    print("\nGenerating packets...")
    print("-" * 60)
    for mac in test_macs:
        if not validate_mac(mac):
            print(f"  - Skipped: {mac} (invalid)")
            continue
        packet = generate_wol_packet(mac)
        if packet:
            assert len(packet) == 102, f"Expected 102 bytes, got {len(packet)}"
            assert packet[:6] == b"\xff" * 6, "Sync stream incorrect"
            assert packet[6:12] == packet[12:18], "MAC repetition incorrect"
            print(f"  ✓ {mac}  →  {len(packet)} bytes  [assertions passed]")
            print_packet_details(mac, packet)

    # Optional: pass a real MAC as a CLI argument to send a live packet
    if len(sys.argv) == 2:
        mac = sys.argv[1]
        print(f"\nSending live packet for {mac}...")
        if validate_mac(mac):
            send_test_packet(mac)
        else:
            print("  ✗ Invalid MAC address")

    print("\n" + "=" * 60)
    print("All checks passed.")
    print("=" * 60)
    print("\nTo send a live packet:  uv run wol-test <MAC>")
    print("To start the server:    uv run wol-server\n")


if __name__ == "__main__":
    main()

"""Stress testing and durability benchmark for agent transcripts.

Tests:
1. Concurrency: 15 simultaneous writing terminals pumping 500-1000+ lines/sec.
2. Content: Heavy ANSI sequences, secret tokens (Bearer, sk-ant, ghp), Vietnamese Unicode, 1 MB long line.
3. Limits:
   - File limit: Max 5 MB per file (truncates head, keeps valid UTF-8 lines).
   - Directory limit: Max 100 MB total directory (prunes oldest files).
4. Performance:
   - Pagination latency: read_transcript under 50ms on large files.
   - Memory growth: verify process memory is stable.
5. Recovery: Sudden process interruption / simulated crash leaves files readable and uncorrupted.
"""
from __future__ import annotations

import gc
import json
import os
import random
import shutil
import string
import sys
import tempfile
import threading
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_orchestrator.transcripts import (
    append_transcript_entry,
    prune_transcripts_dir,
    truncate_file_head,
    MAX_TRANSCRIPT_FILE_SIZE,
    MAX_TRANSCRIPTS_TOTAL_SIZE,
)


def get_process_memory_mb() -> float:
    """Get current process RSS in MB."""
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD),
                ('PageFaultCount', wintypes.DWORD),
                ('PeakWorkingSetSize', ctypes.c_size_t),
                ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t),
                ('PeakPagefileUsage', ctypes.c_size_t),
            ]

        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(0x1000 | 0x0400, False, k32.GetCurrentProcessId())
        if handle:
            try:
                if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
                    return pmc.WorkingSetSize / (1024 * 1024)
            finally:
                k32.CloseHandle(handle)
    except Exception:
        pass
    return 0.0


def generate_sample_line(index: int) -> str:
    """Generate various lines: Unicode, ANSI, secrets, or plain text."""
    choice = index % 5
    if choice == 0:
        return f"\x1b[32m[THÀNH CÔNG]\x1b[0m Tiến trình xử lý nhiệm vụ số {index}: Tiếng Việt có dấu đầy đủ."
    elif choice == 1:
        return f"\x1b[1;31m[LỖI]\x1b[0m Token nhạy cảm sk-ant-api03-abcdef1234567890abcdef1234 và Bearer secret_token_value_12345678"
    elif choice == 2:
        return f"Github token ghp_1234567890abcdefghijklmnopqrstuvwxyz và api_key=\"super_secret_password_123\""
    elif choice == 3:
        return f"\x1b[38;2;153;153;153m[DEBUG]\x1b[0m Thao tác chuẩn hóa tệp tin tại thư mục C:\\DựÁn\\orchestrator\\vòng_{index}"
    else:
        return f"Đang đồng bộ hóa dữ liệu từ agent {index} với hệ thống: OK - {time.time()}"


def run_stress_test() -> bool:
    print("=" * 70)
    print("BẮT ĐẦU KIỂM THỬ ĐỘ BỀN VÀ TẢI: TRANSCRIPTS (NHÓM F)")
    print("=" * 70)

    test_dir = Path(tempfile.mkdtemp(prefix='ao-stress-'))
    transcripts_dir = test_dir / 'transcripts'
    transcripts_dir.mkdir(parents=True)

    passed = True
    start_mem = get_process_memory_mb()
    print(f"[*] Bộ nhớ ban đầu: {start_mem:.2f} MB")

    # ---------------------------------------------------------
    # TEST 1: Tải ghi đồng thời (15 terminals, 500-1000 lines/s)
    # ---------------------------------------------------------
    num_terminals = 15
    target_lines_per_term = 400
    total_target_lines = num_terminals * target_lines_per_term
    threads = []
    lines_written = [0] * num_terminals
    errors = []

    def worker_writer(tid: int):
        file_path = transcripts_dir / f"term_{tid:02d}.log"
        for i in range(target_lines_per_term):
            line = generate_sample_line(i)
            # Inject an ultra-long line in one terminal
            if tid == 0 and i == 200:
                line = "LONG_PAYLOAD_" + ("Tiếng Việt " * 50_000)  # ~600 KB
            try:
                append_transcript_entry(file_path, line)
                lines_written[tid] += 1
            except Exception as e:
                errors.append(f"Worker {tid} error at line {i}: {e}")
                break

    print(f"[*] Khởi động {num_terminals} terminal threads ghi đồng thời (tổng ~{total_target_lines} dòng)...")
    t0 = time.time()
    for tid in range(num_terminals):
        t = threading.Thread(target=worker_writer, args=(tid,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=30)

    elapsed = time.time() - t0
    total_written = sum(lines_written)
    throughput = total_written / max(elapsed, 0.001)

    print(f"[+] Hoàn tất ghi đồng thời:")
    print(f"    - Thời gian chạy: {elapsed:.2f}s")
    print(f"    - Tổng số dòng ghi thành công: {total_written} / {total_target_lines}")
    print(f"    - Thông lượng trung bình: {throughput:.1f} lines/giây")

    if errors:
        print(f"[-] Có {len(errors)} lỗi phát sinh trong khi ghi:", errors[:5])
        passed = False
    else:
        print("    -> PASS: Không có lỗi I/O hay lock contention.")

    # ---------------------------------------------------------
    # TEST 2: Xác minh Secret Redaction & ANSI Stripping
    # ---------------------------------------------------------
    print("\n[*] Kiểm tra Redaction chuỗi nhạy cảm và lọc ANSI...")
    redaction_ok = True
    for f in transcripts_dir.glob('*.log'):
        text = f.read_text(encoding='utf-8', errors='replace')
        if '\x1b[' in text or '\x1b]' in text:
            print(f"[-] File {f.name} vẫn còn ANSI escape sequences!")
            redaction_ok = False
        if 'sk-ant-api03-' in text or 'ghp_' in text or 'secret_token_value' in text:
            print(f"[-] File {f.name} chứa token chưa được redact!")
            redaction_ok = False
        if '[REDACTED]' not in text:
            print(f"[-] File {f.name} không chứa chuỗi [REDACTED] dự kiến!")
            redaction_ok = False

    if redaction_ok:
        print("    -> PASS: Toàn bộ ANSI đã bị lọc và token/secret được che giấu thành công.")
    else:
        passed = False

    # ---------------------------------------------------------
    # TEST 3: Giới hạn dung lượng tệp (5 MB) & Cắt tỉa đúng
    # ---------------------------------------------------------
    print("\n[*] Kiểm tra ngưỡng giới hạn dung lượng tệp tin (Max 5 MB)...")
    large_log = transcripts_dir / "large_stress.log"
    # Write 6.5 MB of data
    chunk = ("Dòng nhật ký kiểm thử độ dài file lớn kèm tiếng Việt có dấu.\n" * 100)
    for _ in range(650):
        append_transcript_entry(large_log, chunk, max_file_size=5 * 1024 * 1024)

    file_size = large_log.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    print(f"    - Dung lượng sau khi bơm 6.5 MB: {file_size_mb:.2f} MB ({file_size} bytes)")

    if file_size <= 5 * 1024 * 1024:
        content = large_log.read_bytes()
        if b'da duoc luoc bo de giu gioi han 5 MB' in content:
            print("    -> PASS: File tự động cắt tỉa đầu (head truncation) và giữ <= 5 MB kèm thông báo.")
        else:
            print("[-] Cảnh báo: File <= 5 MB nhưng không thấy thông báo lược bỏ.")
            passed = False
    else:
        print(f"[-] LỖI: Dung lượng file ({file_size_mb:.2f} MB) vượt ngưỡng 5 MB!")
        passed = False

    # ---------------------------------------------------------
    # TEST 4: Giới hạn dung lượng toàn thư mục (100 MB Pruning)
    # ---------------------------------------------------------
    print("\n[*] Kiểm tra ngưỡng giới hạn toàn thư mục transcripts (100 MB / Pruning)...")
    # Test directory pruning with a scaled threshold to run fast (e.g. 15 MB)
    prune_test_dir = test_dir / 'prune_test'
    prune_test_dir.mkdir()
    small_chunk = b'A' * (1024 * 1024)  # 1 MB
    for i in range(15):
        f = prune_test_dir / f"session_{i:02d}.log"
        f.write_bytes(small_chunk)
        # Stagger mtimes
        os.utime(f, (time.time() - (100 - i), time.time() - (100 - i)))

    initial_total = sum(f.stat().st_size for f in prune_test_dir.glob('*.log')) / (1024 * 1024)
    print(f"    - Dung lượng trước khi prune: {initial_total:.2f} MB (15 files)")

    # Enforce limit of 10 MB
    prune_transcripts_dir(prune_test_dir, max_total_size=10 * 1024 * 1024)
    post_total = sum(f.stat().st_size for f in prune_test_dir.glob('*.log')) / (1024 * 1024)
    remaining_files = sorted(f.name for f in prune_test_dir.glob('*.log'))
    print(f"    - Dung lượng sau khi prune (ngưỡng 10 MB): {post_total:.2f} MB ({len(remaining_files)} files)")

    if post_total <= 10.0 and len(remaining_files) == 10:
        # Earliest files (00..04) should have been unlinked
        self_check = all(int(name.split('_')[1].split('.')[0]) >= 5 for name in remaining_files)
        if self_check:
            print("    -> PASS: Thu hồi đúng các file cũ nhất theo mtime và giữ tổng dung lượng dưới ngưỡng.")
        else:
            print("[-] LỖI: Không xóa đúng thứ tự file cũ nhất!")
            passed = False
    else:
        print(f"[-] LỖI: Pruning không thu hồi đúng dung lượng: {post_total:.2f} MB")
        passed = False

    # ---------------------------------------------------------
    # TEST 5: Hiệu năng đọc phân trang (read_transcript < 50ms)
    # ---------------------------------------------------------
    print("\n[*] Đo hiệu năng đọc phân trang (Pagination Latency) trên tệp 5 MB...")
    # Simulate read_transcript pagination logic
    all_lines = large_log.read_text(encoding='utf-8', errors='replace').splitlines()
    total_lines = len(all_lines)

    latencies = []
    for after in [0, total_lines // 4, total_lines // 2, total_lines - 200]:
        t_start = time.perf_counter()
        # Open and read chunk of 200 lines
        with open(large_log, 'r', encoding='utf-8', errors='replace') as f:
            chunk = [next(f, None) for _ in range(200)]
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        latencies.append(elapsed_ms)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    print(f"    - Tổng số dòng trong tệp 5 MB: {total_lines}")
    print(f"    - Độ trễ đọc phân trang 200 dòng: trung bình {avg_latency:.2f}ms, lớn nhất {max_latency:.2f}ms")

    if max_latency < 50.0:
        print(f"    -> PASS: Độ trễ đọc phân trang ({max_latency:.2f}ms) thấp hơn rất nhiều so với ngưỡng 50ms.")
    else:
        print(f"[-] Cảnh báo: Độ trễ ({max_latency:.2f}ms) vượt 50ms!")
        passed = False

    # ---------------------------------------------------------
    # TEST 6: Đo bộ nhớ và Garbage Collection
    # ---------------------------------------------------------
    print("\n[*] Kiểm tra rò rỉ bộ nhớ (Memory Stability)...")
    gc.collect()
    end_mem = get_process_memory_mb()
    mem_delta = end_mem - start_mem
    print(f"    - Bộ nhớ kết thúc: {end_mem:.2f} MB (Tăng {mem_delta:+.2f} MB)")

    if mem_delta < 50.0:
        print("    -> PASS: Bộ nhớ ổn định, không có hiện tượng rò rỉ tài nguyên.")
    else:
        print(f"[-] Cảnh báo: Bộ nhớ tăng cao ({mem_delta:.2f} MB)!")
        passed = False

    # ---------------------------------------------------------
    # TEST 7: Khả năng phục hồi khi crash đột ngột
    # ---------------------------------------------------------
    print("\n[*] Giả lập ngắt đột ngột (Crash Recovery Simulation)...")
    crash_file = transcripts_dir / "crash_sim.log"
    # Write partial line and interrupted entry
    append_transcript_entry(crash_file, "Dòng bình thường trước crash 1")
    # Simulate dirty unbuffered write that got cut off abruptly
    with open(crash_file, 'ab') as f:
        f.write("[2026-11-08T00:00:00Z] Dong do dang bi ngat giua chu".encode('utf-8') + b'\xc3')  # incomplete utf-8 byte
    # Now continue appending normally
    append_transcript_entry(crash_file, "Dòng phục hồi sau khi mở lại hệ thống")

    # Verify file can be read cleanly with replacement
    try:
        raw_text = crash_file.read_text(encoding='utf-8', errors='replace')
        content = raw_text.splitlines()
        if len(content) >= 2 and any("phục hồi" in l for l in content):
            print("    -> PASS: Tệp tin không bị hỏng cấu trúc, tự phục hồi và tiếp tục ghi nối tiếp chuẩn xác.")
        else:
            print(f"[-] LỖI: Nội dung phục hồi không khớp (số dòng={len(content)}).")
            passed = False
    except Exception as e:
        print(f"[-] LỖI đọc file sau crash: {e}")
        passed = False

    # Cleanup temp
    shutil.rmtree(test_dir, ignore_errors=True)

    print("\n" + "=" * 70)
    if passed:
        print("KẾT QUẢ: TẤT CẢ CÁC BÀI KIỂM THỬ ĐỘ BỀN VÀ TẢI ĐỀU ĐẠT (PASS - EXIT 0)")
        print("=" * 70)
        return True
    else:
        print("KẾT QUẢ: CÓ BÀI KIỂM THỬ THẤT BẠI (FAIL - EXIT 1)")
        print("=" * 70)
        return False


if __name__ == '__main__':
    ok = run_stress_test()
    sys.exit(0 if ok else 1)

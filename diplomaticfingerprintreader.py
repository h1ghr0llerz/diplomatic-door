import sys
sys.path.append("./PyGT-521F32")
import os
import serial
import threading
import GT521F32
import utilities.door_client


class DiplomaticFingerprintReader(object):
    def __init__(self, fingerprint_port, permitted_user_ids):
        self._fingerprint_port = fingerprint_port
        self._permitted_user_ids = permitted_user_ids
        self._setup = False
        self._thread = None
        self._stop = threading.Event()

    def setup(self):
        assert not self._setup

        try:
            self._fingerprint_device = GT521F32.GT521F32(self._fingerprint_port)
        except GT521F32.GT521F32Exception as e:
            pass
        else:
            self._fingerprint_device.open()
            #self._fingerprint_device.change_baud_rate_and_reopen(115200) # causes issues after reconnect
            self._setup = True

        return self._setup

    def _worker(self):
        while not self._stop.is_set():
            user_id = self._fingerprint_device.identify()
            if user_id in self._permitted_user_ids:
                self._open_door()
            else:
                print("Access denied.")

    def start(self):
        assert self._setup

        self._stop.clear()
        self._thread = threading.Thread(
                        target=self._worker,
                    )
        self._thread.start()
        
    def _open_door(self):
        print("Opening door")
        utilities.door_client.client_open_door()

    def stop(self):
        assert self._setup
        assert self._thread is not None
        if self._thread.is_alive():
            self._stop.set()
            self._fingerprint_device.cancel()
            self._thread.join(5)
            
    def close(self):
        self._fingerprint_device.close()

        

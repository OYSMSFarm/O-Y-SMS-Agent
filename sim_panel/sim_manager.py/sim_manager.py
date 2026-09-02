import serial
import time
import re
from database import update_sim_status, get_all_sims

class ModemDriver:
    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
    
    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(1)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def send_at(self, command, wait=1):
        if not self.ser:
            return None
        
        try:
            self.ser.write(f'{command}\r\n'.encode())
            time.sleep(wait)
            response = self.ser.read_all().decode('utf-8', errors='ignore')
            return response.strip()
        except Exception as e:
            print(f"AT command failed: {e}")
            return None
    
    def get_imsi(self):
        response = self.send_at('AT+CRSM=176,0,0,0,12')
        if response and '00' in response:
            return response.split(',')[2] if ',' in response else None
        return None
    
    def get_imei(self):
        response = self.send_at('AT+GSN', 2)
        if response and response.isdigit():
            return response
        return None
    
    def get_iccid(self):
        response = self.send_at('AT+CCID', 2)
        if response and '00' in response:
            return response.split(',')[1].strip() if ',' in response else None
        return None
    
    def get_signal(self):
        response = self.send_at('AT+CSQ', 2)
        if response and ',' in response:
            signal = response.split(',')[1].strip()
            if signal.isdigit():
                return int(signal)
        return None
    
    def get_network(self):
        response = self.send_at('AT+COPS?', 2)
        if response and 'COPS:' in response:
            parts = response.split(',')
            if len(parts) >= 4:
                return parts[3].strip('"')
        return None
    
    def get_phone_number(self):
        response = self.send_at('AT+CNUM', 2)
        if response and 'CNUM:' in response:
            match = re.search(r'"([^"]*)"', response)
            if match:
                return match.group(1)
        return None
    
    def send_ussd(self, code):
        self.send_at('AT+CUSD=1,"' + code + '",15')
        time.sleep(3)
        response = self.send_at('AT+CUSD?')
        if response and 'CUSD:' in response:
            match = re.search(r'"([^"]*)"', response)
            if match:
                return match.group(1)
        return None
    
    def disconnect(self):
        if self.ser:
            self.ser.close()
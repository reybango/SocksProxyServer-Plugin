from __future__ import print_function
import importlib

if importlib.util.find_spec("empire") is not None:
    from empire.server.common.plugins import Plugin
    import empire.server.common.helpers as helpers    
else:
    from lib.common.plugins import Plugin
    import lib.common.helpers as helpers    

import socket
import _thread
import ssl
import queue
import os


class Plugin(Plugin):
    description = "Launches a Socks Proxy Server to run in the background of Empire"

    def onLoad(self):
        """ any custom loading behavior - called by init, so any
        behavior you'd normally put in __init__ goes here """
        self.info = {
                        'Name': 'socksproxyserver',

                        'Author': ['@Cx01N', '@mjokic'],

                        'Description': ('Launches a Socks Proxy Server to run in the background of Empire.'),

                        'Software': '',

                        'Techniques': [''],

                        'Comments': []
                    },

        self.options = {
                    'status': {
                        'Description': 'Start/stop the Chisel server. Specify a port or default to 8080.',
                        'Required': True,
                        'Value': 'start'
                    },
                    'handlerport': {
                        'Description': 'Port number.',
                        'Required': True,
                        'Value': '443'
                    },
                    'proxyport': {
                        'Description': 'Port number.',
                        'Required': True,
                        'Value': '1080'
                    },
                    'certificate': {
                        'Description': 'Certifcate directory [Default: Empire self-signed cert].',
                        'Required': False,
                        'Value': ''
                    },
                    'privatekey': {
                        'Description': 'Private key directory [Default: Empire private key]',
                        'Required': False,
                        'Value': ''
                    },
        }


        # load default empire certs
        self.cert_path = os.path.abspath("./data/")
        self.certificate = "%s/empire-chain.pem" % self.cert_path
        self.private_key = "%s/empire-priv.key" % self.cert_path

        self.running = False

    def execute(self, command):
        # This is for parsing commands through the api
        try:
            # essentially switches to parse the proper command to execute
            self.options['status']['Value'] = command['status']
            self.options['handlerport']['Value'] = command['handlerport']
            self.options['proxyport']['Value'] = command['proxyport']
            self.options['certificate']['Value'] = command['certificate']
            self.options['privatekey']['Value'] = command['privatekey']
            results = self.do_socksproxyserver('')
            return results
        except:
            return False

    def get_commands(self):
        return self.commands

    def register(self, main_menu):
        """ any modifications to the mainMenu go here - e.g.
        registering functions to be run by user commands """
        main_menu.__class__.do_socksproxyserver = self.do_socksproxyserver

    def do_socksproxyserver(self, args):
        "Launches a SocksProxy Server to run in the background of Empire"

        if not args:
            # Load defaults for server
            self.status = self.options['status']['Value']
            self.handler_port = self.options['handlerport']['Value']
            self.proxy_port = self.options['proxyport']['Value']

            if not self.options['certificate']['Value'] or self.options['privatekey']['Value']:
                # load default empire certs
                self.cert_path = os.path.abspath("./data/")
                self.certificate = "%s/empire-chain.pem" % self.cert_path
                self.private_key = "%s/empire-priv.key" % self.cert_path

            print(helpers.color(
                "[!] Usage: socksserver <start|stop> [handler port] [proxy port] [certificate] [private key]"))
            print(helpers.color(
                "[+] Defaults: socksserver " + self.status + " " + self.handler_port + " " + self.proxy_port + " " +
                self.certificate + " " + self.private_key))

        else:
            args = args.split(" ")

            # Check server status
            if args[0].lower() == "start":
                self.status = 'start'
            elif args[0].lower() == "stop":
                self.status = 'stop'
            # Check for port numbers
            if len(args) > 2:
                self.handler_port = args[1]
                self.proxy_port = args[2]
            else:
                self.handler_port = self.options['handlerport']['Value']
                self.proxy_port = self.options['proxyport']['Value']

            # Check for certificates
            if len(args) > 4:
                self.certificate = args[3]
                self.private_key = args[4]
            else:
                # load default empire certs
                self.cert_path = os.path.abspath("./data/")
                self.certificate = "%s/empire-chain.pem" % self.cert_path
                self.private_key = "%s/empire-priv.key" % self.cert_path

        # Switch for starting and stopping server
        if self.status == "start":
            self.start_socks_server()
        elif self.status == "stop":
            self.shutdown()
        else:
            print(helpers.color("[!] Usage: socksserver <start|stop> [handler port] [proxy port] [certificate] ["
                                "private key]"))

    def start_socks_server(self):
        if not self.running:
            self.running = True
            _thread.start_new_thread(self.server,
                                     (self.handler_port, self.proxy_port, self.certificate, self.private_key))
        else:
            print(helpers.color("[!] Socks Proxy Server Already Running!"))

    def shutdown(self):
        """if the plugin spawns a process provide a shutdown method for when Empire exits else leave it as pass"""
        if self.running:
            self.running = False
            print(helpers.color("[*] Stopping socks proxy server..."))
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("127.0.0.1", int(self.handler_port)))
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("127.0.0.1", int(self.proxy_port)))
        else:
            print(helpers.color("[!] Server is not running!"))

    def handler_server(self, q, handler_port, certificate, private_key):
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        context.load_cert_chain(certificate, private_key)
        try:
            dock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            dock_socket.bind(('', int(handler_port)))
            dock_socket.listen(5)
            print(helpers.color("[*] Handler listening on: " + handler_port))
            print(helpers.color("[*] Using certificate: " + certificate))
            print(helpers.color("[*] Using private key: " + private_key))
            print(helpers.color("[+] Socks proxy server started"))
            while self.running:
                try:
                    clear_socket, address = dock_socket.accept()
                    client_socket = context.wrap_socket(clear_socket, server_side=True)
                    try:
                        data = b""
                        while data.count(b'\n') < 3:
                            data_recv = client_socket.recv()
                            data += data_recv
                        client_socket.send(
                            b"HTTP/1.1 200 OK\nContent-Length: 999999\nContent-Type: text/plain\nConnection: Keep-Alive\nKeep-Alive: timeout=20, max=10000\n\n")
                        q.get(False)
                    except Exception as e:
                        pass
                    q.put(client_socket)
                except Exception as e:
                    pass
        except Exception as e:
            pass
        finally:
            dock_socket.close()

    def get_active_connection(self, q):
        try:
            client_socket = q.get(block=True, timeout=10)
        except:
            return None
        try:
            client_socket.send(b"HELLO")
        except:
            return self.get_active_connection(q)
        return client_socket

    def server(self, handler_port, proxy_port, certificate, private_key):
        q = queue.Queue()
        _thread.start_new_thread(self.handler_server, (q, handler_port, certificate, private_key))
        try:
            dock_socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dock_socket2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            dock_socket2.bind(('127.0.0.1', int(proxy_port)))
            dock_socket2.listen(5)
            print(helpers.color("\n[*] Socks server listening on: " + proxy_port))
            while self.running:
                try:
                    client_socket2, address = dock_socket2.accept()
                    client_socket = self.get_active_connection(q)
                    if client_socket == None:
                        client_socket2.close()
                    _thread.start_new_thread(self.forward, (client_socket, client_socket2))
                    _thread.start_new_thread(self.forward, (client_socket2, client_socket))
                except Exception as e:
                    print(helpers.color("[!] Exception: %s" % e))
        except Exception as e:
            print(helpers.color("[!] Exception: %s" % e))
        finally:
            dock_socket2.close()
            print(helpers.color("\n[+] Socks proxy server stopped"))

    def forward(self, source, destination):
        try:
            string = ' '
            while string:
                string = source.recv(1024)
                if string:
                    destination.sendall(string)
                else:
                    source.shutdown(socket.SHUT_RD)
                    destination.shutdown(socket.SHUT_WR)
        except:
            try:
                source.shutdown(socket.SHUT_RD)
                destination.shutdown(socket.SHUT_WR)
            except:
                pass
            pass

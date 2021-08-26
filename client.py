import asyncio
import argparse

class Client:
    def __init__(self, ip='127.0.0.1', port=15720, name='Riley'):
        '''
        127.0.0.1 is the localhost
        port could be any port
        '''
        self.ip = ip
        self.port = port
        self.name = name

    async def tcp_echo_client(self, message, loop):
        '''
        on client side send the message for echo
        '''
        reader, writer = await asyncio.open_connection(self.ip, self.port,
                                                       loop=loop)
        print('{} send: {}'.format(self.name, message))
        writer.write(message.encode())

        data = await reader.read(100000)
        print('{} received: {}'.format(self.name, data.decode()))

        print('close the socket')
        writer.close()
        await writer.wait_closed()

    def run_until_quit(self):
        # start the loop
        loop = asyncio.get_event_loop()
        while True:
            # collect the message to send
            message = input("Please input the next message to send: ")
            if message in ['quit', 'exit', ':q', 'exit;', 'quit;', 'exit()', '(exit)']:
                break
            else:
                message += '\n'
                loop.run_until_complete(self.tcp_echo_client(message, loop))
        loop.close()

if __name__ == '__main__':
    client = Client() # using the default settings
    client.run_until_quit()

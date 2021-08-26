import asyncio
import aiohttp
import json
import time
import sys
import logging


MY_KEY = "[REDACTED]"

ports = { "Riley": 15720, "Jaquez": 15721, "Juzang": 15722, "Campbell": 15723, "Bernard": 15724 }

connections = { "Riley": ["Jaquez", "Juzang"],
                "Jaquez": ["Riley", "Bernard"],
                "Juzang": ["Riley", "Campbell", "Bernard"],
                "Campbell": ["Bernard", "Juzang"],
                "Bernard": ["Jaquez", "Juzang", "Campbell"] }

class Server:
    def __init__(self, name, localhost='127.0.0.1'):
        self.name = name
        self.localhost = localhost
        self.port = ports[name]
        self.clients = {}
        self.message = {}
        logging.info("{}".format(name))
        
    async def accept_arg(self, reader, writer):
        while not reader.at_eof():
            info = await reader.readline()
            my_msg = info.decode()
            my_msg = my_msg[:-1]
            elements = my_msg.split()
            logging.info("{} Received: {}".format(self.name, my_msg))
            send_out = None
            arglen = len(elements)
            if arglen != 4 or (elements[0] != "IAMAT" and elements[0] != "WHATSAT" and elements[0] != "AT"):
                if arglen == 6 and elements[0] == "AT":
                    logging.info("Received message:")
                    new_info = float(elements[5])
                    if elements[3] in self.clients:
                        logging.info("Already got info for client {}".format(elements[3]))
                        
                        if float(elements[5]) > self.clients[elements[3]]:
                            logging.info("Client {} info being updated and dispersing new info".format(elements[1]))
                            self.clients[elements[3]] = new_info
                            self.message[elements[3]] = my_msg
                            await self.disperse_msg(my_msg)
                        else:
                            logging.info("Already receieved message")
                            pass
                    else:
                        logging.info("Client {} got new info and dispersing it".format(elements[1]))
                        self.clients[elements[3]] = new_info
                        self.message[elements[3]] = my_msg
                        await self.disperse_msg(my_msg)
                else:
                    send_out = "? " + my_msg
            elif elements[0] == "WHATSAT":
                isValid = 1
                second = elements[2]
                third = elements[3]
                if not (second.replace('.','',1).isdigit() and third.replace('.','',1).isdigit()):
                    isValid = 0
                if int(second) < 0 or int(second) > 50:
                    isValid = 0
                if int(third) < 0 or int(third) > 20:
                    isValid = 0
                if elements[1] not in self.clients:
                    isValid = 0
                if isValid == 1:
                    radius = second
                    constraint = third
                    area = self.message[elements[1]].split()[4]
                    google = await self.google_places(area, radius, constraint)
                    google_str = str(google)
                    send_out = "{}\n{}\n\n".format(self.message[elements[1]],google_str.strip("\n"))
                else:
                    send_out = "? " + my_msg
            elif elements[0] == "IAMAT":
                first = elements[1]
                second = elements[2]
                third = elements[3]
                elem = list(filter(None, (second.replace("+","-")).split("-")))
                elemlen = len(elem)
                isValid = 1
                if elemlen != 2 or not (elem[0].replace('.','',1).isdigit() and elem[1].replace('.','',1).isdigit()):
                    isValid = 0
                if not third.replace('.','',1).isdigit():
                    isValid = 0
                if isValid == 1:
                    time_diff = time.time() - float(third)
                    send_out = "AT {} {} {} {} {}".format(self.name, time_diff, first, second, third)
                    send_out += "\n"
                    self.clients[first] = float(third)
                    self.message[first] = send_out
                    await self.disperse_msg(send_out)
                else:
                    send_out = "? " + my_msg
            else:
                send_out = "? " + my_msg
            if send_out != None:
                logging.info("Sending {} to client".format(send_out))
                writer.write(send_out.encode())
        await writer.drain()
        writer.close()

    async def disperse_msg(self, msg):
        for server in connections[self.name]:
            logging.info("Starting connection to server {}".format(server))
            try:
                reader, writer = await asyncio.open_connection(self.localhost, ports[server])
                logging.info("Connected to {}".format(server))
                my_msg = msg + "\n"
                writer.write(my_msg.encode())
                logging.info("Sent {} to server: {}".format(msg, server))
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                logging.info("Connection closed with: {}".format(server))
            except:
                logging.info("Error trying to connect with server {}".format(server))
    
    async def google_places(self, area, radius, constraint):
        async with aiohttp.ClientSession() as session:
            positive = area.rfind("+")
            negative = area.rfind("-")
            coords = None
            if positive > 0:
                coords = "{},{}".format(area[0:positive],area[positive:])
            elif negative > 0:
                coords = "{},{}".format(area[0:negative],area[negative:])
            if coords == None:
                sys.stderr("BAD COORDS!")
                sys.exit()
            logging.info("Trying to get places info at {}".format(coords))
            my_url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={}&radius={}&key={}'.format(coords, radius, MY_KEY)
            async with session.get(my_url) as response:
                json_string = await response.text()
                json_object = json.loads(json_string)
                json_results = len(json_object["results"])
                logging.info("Received {} from places".format(json_results))
                constr_int = int(constraint)
                if constr_int >= json_results:
                    return json_string
                else:
                    json_object["results"] = json_object["results"][0:constr_int]
                    return json.dumps(json_object,indent=4) + "\n\n"

    async def run_til_interrupt(self):
        
        logging.info("Starting up server {}".format(self.name))
        server = await asyncio.start_server(self.accept_arg, self.localhost, self.port)

        async with server:
            await server.serve_forever()
            
        server.close()
        logging.info("Closing up server {}".format(self.name))
        
if __name__ == '__main__':

    arglen = len(sys.argv)
    if arglen != 2:
        sys.stderr("BAD ARGUMENT")
        sys.exit()

    name = sys.argv[1]
    if name not in ports:
        sys.stderr("INCORRECT NAME, PLEASE CHOOSE: Riley, Jaquez, Juzang, Campbell, or Bernard")
        sys.exit()

    logging.basicConfig(filename="server_{}.log".format(name), filemode='w', level=logging.INFO)
    serv = Server(name)
    try:
        asyncio.run(serv.run_til_interrupt())
    except KeyboardInterrupt:
        pass
    

            
        

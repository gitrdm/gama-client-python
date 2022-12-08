import json
import sys
import threading
from asyncio import Future

import websockets
import asyncio
from typing import List, Dict, Union, Callable, Any
import uuid
from gama_client.command_types import CommandTypes
from gama_client.message_types import MessageTypes


class GamaBaseClient:

    # CLASS VARIABLES
    event_loop: asyncio.AbstractEventLoop
    socket: websockets.WebSocketClientProtocol
    socket_id: str
    url: str
    port: int
    message_handler: Callable

    def __init__(self, url: str, port: int, message_handler: Callable[[Dict], Any]):
        """
        Initialize the client. At this point no connection is made yet.
        :param url: a string representing the url (or ip address) where the gama-server is running
        :param port: an integer representing the port on which the server runs
        """
        self.url                = url
        self.port               = port
        self.message_handler    = message_handler
        self.socket_id          = ""
        self.socket             = None
        self.event_loop         = asyncio.get_running_loop()
        self.connection_future  = None

    async def connect(self, set_socket_id: bool = True):
        """
        Tries to connect the client to gama-server using the url and port given at the initialization.
        Can throw exceptions in case of connection problems.
        Once the connection is done it runs start_listening_loop and sets socket_id if set
        """
        self.connection_future = self.event_loop.create_future()
        self.socket = await websockets.connect(f"ws://{self.url}:{self.port}")
        self.event_loop.create_task(self.start_listening_loop(set_socket_id))
        if set_socket_id:
            self.socket_id = await self.connection_future

    async def start_listening_loop(self, handle_connection_message: bool):
        while True:
            try:
                mess = await self.socket.recv()
                try:
                    js = json.loads(mess)
                    if handle_connection_message and "type" in js and "content" in js and js["type"] == MessageTypes.ConnectionSuccessful.value:
                        self.connection_future.set_result(js["content"])
                    else:
                        await self.message_handler(js)
                except Exception as js_ex:
                    print("Unable to unpack gama-server messages as a json", js_ex)
            except Exception as sock_ex:
                print("Error while waiting for a message from gama-server. Exiting", sock_ex)
                sys.exit(-1)


    async def load(self, file_path: str, experiment_name: str, console: bool = False, status: bool = False, dialog: bool = False, parameters: List[Dict] = None, until: str = "", additional_data: Dict = None):
        cmd = {
            "type": CommandTypes.Load.value,
            "socket_id": self.socket_id,
            "model": file_path,
            "experiment": experiment_name,
            "console": console,
            "status": status,
            "dialog": dialog,
        }
        #adding optional parameters
        if parameters:
            cmd["parameters"] = parameters
        if until and until != '':
            cmd["until"] = until
        if additional_data:
            cmd.update(additional_data)

        await self.socket.send(json.dumps(cmd))

    async def exit(self):
        cmd = {
            "type": CommandTypes.Exit.value
        }
        await self.socket.send(json.dumps(cmd))

    async def play(self, exp_id: str, sync: bool = False, additional_data: Dict = None):
        cmd = {
            "type": CommandTypes.Play.value,
            "socket_id": self.socket_id,
            "exp_id": exp_id,
            "sync": sync,
        }
        if additional_data:
            cmd.update(additional_data)

        await self.socket.send(json.dumps(cmd))

    async def pause(self, exp_id: str, additional_data: Dict = None):
        cmd = {
            "type": CommandTypes.Pause.value,
            "socket_id": self.socket_id,
            "exp_id": exp_id,
        }
        if additional_data:
            cmd.update(additional_data)

        await self.socket.send(json.dumps(cmd))


    async def step(self, exp_id: str, nb_step: int = 1, sync: bool = False, additional_data: Dict = None):
        cmd = {
            "type": CommandTypes.Step.value,
            "socket_id": self.socket_id,
            "exp_id": exp_id,
            "sync": sync,
        }
        if nb_step > 1:
            cmd["nb_step"] = nb_step
        if additional_data:
            cmd.update(additional_data)

        await self.socket.send(json.dumps(cmd))



    async def step_back(self, exp_id: str, nb_step: int = 1, sync: bool = False, additional_data: Dict = None):
        cmd = {
            "type": CommandTypes.StepBack.value,
            "socket_id": self.socket_id,
            "exp_id": exp_id,
            "sync": sync,
        }
        if nb_step > 1:
            cmd["nb_step"] = nb_step
        if additional_data:
            cmd.update(additional_data)

        await self.socket.send(json.dumps(cmd))



    async def stop(self, exp_id: str, additional_data: Dict = None):
        cmd = {
            "type": CommandTypes.Stop.value,
            "socket_id": self.socket_id,
            "exp_id": exp_id,
        }
        if additional_data:
            cmd.update(additional_data)

        await self.socket.send(json.dumps(cmd))


    async def reload(self, exp_id: str, parameters: List[Dict] = None, until: str = "", additional_data: Dict = None):
        cmd = {
            "type": CommandTypes.Reload.value,
            "socket_id": self.socket_id,
            "exp_id": exp_id,
        }
        #adding optional parameters
        if parameters:
            cmd["parameters"] = parameters
        if until and until != '':
            cmd["until"] = until
        if additional_data:
            cmd.update(additional_data)
        await self.socket.send(json.dumps(cmd))


    async def expression(self, exp_id: str, expression: str, additional_data: Dict = None):
        cmd = {
            "type": CommandTypes.Expression.value,
            "socket_id": self.socket_id,
            "exp_id": exp_id,
            "expr": expression
        }
        if additional_data:
            cmd.update(additional_data)

        await self.socket.send(json.dumps(cmd))









import json
import sys

import websockets
import asyncio
from typing import List, Dict, Callable, Any
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
        :param message_handler: a function that will be called every time a message is received from gama-server
        """
        self.url = url
        self.port = port
        self.message_handler = message_handler
        self.socket_id = ""
        self.socket = None
        self.event_loop = asyncio.get_running_loop()
        self.connection_future = None

    async def connect(self, set_socket_id: bool = True):
        """
        Tries to connect the client to gama-server using the url and port given at the initialization.
        Once the connection is done it runs **start_listening_loop** and sets **socket_id** if set

        :param set_socket_id: if true, the listening loop will filter out the messages of type ConnectionSuccessful and
            the GamaClient will set its socket_id itself. If set to false, the users will have to set the client's
            socket_id field themselves in the message_handler function
        :returns: Returns either once the listening loop starts if set_socket_id is False or when a socket_id is
            sent by gama-server
        :raise Exception: Can throw exceptions in case of connection problems.
        """
        self.connection_future = self.event_loop.create_future()
        self.socket = await websockets.connect(f"ws://{self.url}:{self.port}")
        self.event_loop.create_task(self.start_listening_loop(set_socket_id))
        if set_socket_id:
            self.socket_id = await self.connection_future

    async def start_listening_loop(self, handle_connection_message: bool):
        """
        Internal method. It starts an infinite listening loop that will transmit gama-server's messages to the
        message_handler function

        :param handle_connection_message: if set to true, the function checks for messages of type ConnectionSuccessful
            and will set its content field as the result of connection_future that is used in connect to wait for the socket_id
        :return: never returns
        """
        while True:
            try:
                mess = await self.socket.recv()
                try:
                    js = json.loads(mess)
                    if handle_connection_message \
                        and "type" in js \
                        and "content" in js \
                        and js["type"] == MessageTypes.ConnectionSuccessful.value:

                        self.connection_future.set_result(js["content"])
                    else:
                        await self.message_handler(js)
                except Exception as js_ex:
                    print("Unable to unpack gama-server messages as a json", js_ex)
            except Exception as sock_ex:
                print("Error while waiting for a message from gama-server. Exiting", sock_ex)
                sys.exit(-1)

    async def load(self, file_path, experiment_name: str, console: bool = False, status: bool = False,
                   dialog: bool = False, parameters: List[Dict] = None, until: str = "", additional_data: Dict = None):
        """Sends a command to load the experiment **experiment_name** from the file **file_path** (on the server side).

        **Note**
            The parameters must follow this format: ::

                {
                    "type": "<type of the parameter>",
                    "value": "<value of the parameter>",
                    "name": "<name of the parameter in the gaml file>"
                }

            Example value of parameters: ``[{"type": "float", "value": "0.75", "name": "conversion_rate"}]``

        :param file_path: The path of the file containing the experiment to run
        :param experiment_name: the name of the experiment to run
        :param console: True if you want gama-server to redirect the simulation's console outputs
        :param status: True if you want gama-server to redirect the simulation's status changes
        :param dialog: True if you want gama-server to redirect the simulation's dialogs
        :param parameters: a list of dictionaries, each dictionary representing the initial value of an experiment parameter.
            They will be set at the initialization phase of the experiment.
        :param until: a string representing an ending condition to stop an experiment run by gama-server.
            It must be expressed in the gaml language.
        :param additional_data: A dictionary containing any additional data you want to send to gama server. Those will
            be sent back with the command's answer. (for example an id for the client's internal use)

        :returns: If everything goes well on the server side, gama-server will send back a message containing the
            experiment's id.
        """
        cmd = {
            "type": CommandTypes.Load.value,
            "socket_id": self.socket_id,
            "model": file_path,
            "experiment": experiment_name,
            "console": console,
            "status": status,
            "dialog": dialog,
        }
        # adding optional parameters
        if parameters:
            cmd["parameters"] = parameters
        if until and until != '':
            cmd["until"] = until
        if additional_data:
            cmd.update(additional_data)

        await self.socket.send(json.dumps(cmd))

    async def exit(self):
        """
        Sends a command to kill gama-server

        :return: nothing
        """
        cmd = {
            "type": CommandTypes.Exit.value
        }
        await self.socket.send(json.dumps(cmd))

    async def play(self, exp_id: str, sync: bool = False, additional_data: Dict = None):
        """
        Sends a command to run the experiment **exp_id**

        :param exp_id: the id of the experiment on which the command applies
            (sent by gama-server after the load command)
        :param sync: boolean used to specify if the simulation must send a message once the command is received, or wait
            until the end condition is reached. Note: it only works if you previously set a value for the parameter
            *until* in the "load" command.
        :param additional_data: A dictionary containing any additional data you want to send to gama server. Those will
            be sent back with the command's answer. (for example an id for the client's internal use)
        :return: nothing
        """
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
        """
        Sends a command to pause the experiment **exp_id**

        :param exp_id: the id of the experiment to run on which the command applies
            (sent by gama-server after the load command)
        :param additional_data: A dictionary containing any additional data you want to send to gama server. Those will
            be sent back with the command's answer. (for example an id for the client's internal use)
        :return: nothing
        """
        cmd = {
            "type": CommandTypes.Pause.value,
            "socket_id": self.socket_id,
            "exp_id": exp_id,
        }
        if additional_data:
            cmd.update(additional_data)

        await self.socket.send(json.dumps(cmd))

    async def step(self, exp_id: str, nb_step: int = 1, sync: bool = False, additional_data: Dict = None):
        """
        Sends a command to run **nb_step** of the experiment **exp_id**

        :param exp_id: the id of the experiment on which the command applies
            (sent by gama-server after the load command)
        :param nb_step: the number of steps to execute
        :param sync: If True gama-server will wait for the step(s) to finish before sending a success message, else
            the message will be sent as soon as the steps are planned by gama-server.
        :param additional_data: A dictionary containing any additional data you want to send to gama server. Those will
            be sent back with the command's answer. (for example an id for the client's internal use)
        :return: nothing
        """
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
        """
        Sends a command to run **nb_step** steps backwards of the experiment **exp_id**

        :param exp_id: the id of the experiment on which the command applies
            (sent by gama-server after the load command)
        :param nb_step: the number of steps to execute
        :param sync: If True gama-server will wait for the step(s) to finish before sending a success message, else
            the message will be sent as soon as the steps are planned by gama-server.
        :param additional_data: A dictionary containing any additional data you want to send to gama server. Those will
            be sent back with the command's answer. (for example an id for the client's internal use)
        :return: nothing
        """
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
        """
        Sends a command to stop (kill) the experiment **exp_id**

        :param exp_id: the id of the experiment on which the command applies
            (sent by gama-server after the load command)
        :param additional_data: A dictionary containing any additional data you want to send to gama server. Those will
            be sent back with the command's answer. (for example an id for the client's internal use)
        :return: nothing
        """
        cmd = {
            "type": CommandTypes.Stop.value,
            "socket_id": self.socket_id,
            "exp_id": exp_id,
        }
        if additional_data:
            cmd.update(additional_data)

        await self.socket.send(json.dumps(cmd))

    async def reload(self, exp_id: str, parameters: List[Dict] = None, until: str = "", additional_data: Dict = None):
        """
        Sends a command to reload (kill + load again) the experiment **exp_id**. You can reset the experiment's
        parameters as well as the end condition.

        :param exp_id: the id of the experiment on which the command applies
            (sent by gama-server after the load command)
        :param parameters: a list of dictionaries, each dictionary representing the initial value of an experiment parameter.
            They will be set at the initialization phase of the experiment.
        :param until: a string representing an ending condition to stop an experiment run by gama-server.
            It must be expressed in the gaml language.
        :param additional_data: A dictionary containing any additional data you want to send to gama server. Those will
            be sent back with the command's answer. (for example an id for the client's internal use)
        :return: nothing
        """
        cmd = {
            "type": CommandTypes.Reload.value,
            "socket_id": self.socket_id,
            "exp_id": exp_id,
        }
        # adding optional parameters
        if parameters:
            cmd["parameters"] = parameters
        if until and until != '':
            cmd["until"] = until
        if additional_data:
            cmd.update(additional_data)
        await self.socket.send(json.dumps(cmd))

    async def expression(self, exp_id: str, expression: str, additional_data: Dict = None):
        """
        Sends a command to evaluate a gaml expression in the experiment **exp_id**

        :param exp_id: the id of the experiment on which the command applies
            (sent by gama-server after the load command)
        :param expression: the expression to evaluate. Must follow the gaml syntax.
        :param additional_data: A dictionary containing any additional data you want to send to gama server. Those will
            be sent back with the command's answer. (for example an id for the client's internal use)
        :return: The result of the evaluation of the expression will be sent back to the user and caught by the
            listening_loop
        """
        cmd = {
            "type": CommandTypes.Expression.value,
            "socket_id": self.socket_id,
            "exp_id": exp_id,
            "expr": expression
        }
        if additional_data:
            cmd.update(additional_data)

        await self.socket.send(json.dumps(cmd))

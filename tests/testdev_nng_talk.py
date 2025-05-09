import asyncio
from cuemsutils.CommunicatorServices import Communicator

address = "ipc:///tmp/libmtcmaster.sock"
command = {'cmd': 'play'}

async def main():
    await Communicator(address).send_request(command)

if __name__ == "__main__":
    asyncio.run(main())

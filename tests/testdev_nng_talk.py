import asyncio
from cuemsutils.ComunicatorServices import Comunicator

address = "ipc:///tmp/libmtcmaster.sock"
command = {'cmd': 'play'}

async def main():
    await Comunicator(address).send_request(command)

if __name__ == "__main__":
    asyncio.run(main())

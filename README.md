# File Dispatch

File dispatch is an [asyncio](https://docs.python.org/3.9/library/asyncio.html) based directory watcher that 
basically watch a directory for some configured file extension and send the received file
to some configured destination.

## Project structure

## Usage

## Features

+ Support Local file moving
+ Support Http raw file upload (upload file in request body)
+ Support Ftp file upload 
+ Provide a monitoring Api
+ Well tested project
+ ...

## Main dependencies

+ [pydantic](https://pydantic-docs.helpmanual.io/)
+ [mode](https://github.com/ask/mode)
+ [watchfiles](https://watchfiles.helpmanual.io/)
+ [aiohttp](https://docs.aiohttp.org/en/stable/)
+ [aioftp](https://github.com/aio-libs/aioftp)
+ [aiofiles](https://pypi.org/project/aiofiles/)
+ [pipyka](https://github.com/kayak/pypika)
+ [aiosqlite](https://aiosqlite.omnilib.dev/en/stable/)

## Tests

## kowns Issues
+ Users that use python 3.10 can have little issues with **mode**, module since in release 10, the python removes the possibility ot pass **loop** kwargs to **wait** and **wait_for** in **asyncio** module. I have made
little changes on the module to [fix](https://github.com/aristidebm/mode) the problem, it can help but It is not tested. 

## Licence
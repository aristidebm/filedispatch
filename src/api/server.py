##### --- choix technique ----

# It will be good if we can use this server as runtime dependency (https://github.com/ask/mode#what-is-mode) of file dispatch.
# https://docs.aiohttp.org/en/stable/web_quickstart.html

# The api must expose

# - POST /api/logs/
# - GET /api/logs/
# - GET /api/logs/<id>
# - DELETE /api/logs/<id>

# It must expose filters

# - By creation date
# - By transaction state [SUCCEED|FAILURE]
# - By destination
# - By file size
# - By file extension
# - By file name
# - By used protocol

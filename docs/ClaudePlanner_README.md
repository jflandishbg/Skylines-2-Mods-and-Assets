# ClaudePlanner (Cities: Skylines II mod)

A **read-only** planning mod. When a map or save finishes loading, it reads the terrain, the water,
the forests and the outside connections, then writes a master plan for where a real city would
grow. It never places, changes or deletes anything in the game.

## What it decides
- **Old town / centre:** flat, dry land beside sheltered, deep water. A river mouth and nearness to the highway connection count in its favour.
- **Port and industry:** where deep water comes closest to flat land, a short way from the centre, with industry behind the quays.
- **Airport:** a flat 3.4 km runway site 3 to 10 km out, with clear approaches over water or open country.
- **Twin town:** the best harbour site on another landmass, linked at the narrowest crossing.
- **Inner districts and suburbs:** measured over land from the centre, never jumping across water.
- **Green belt and flood plain:** the woods near the city and the low land by the water are left alone.
- **Motorway:** a bypass between the highway connections that skirts the centre, with spurs to the centre and the port.
- **Railway:** from the rail connections to a central station, on to the port and the airport, on easy gradients.

## Where things are
- Source: `C:\Users\<you>\CS2Planner\ClaudePlanner\` (build with `C:\Users\<you>\.dotnet\dotnet.exe build -c Release`; it deploys itself)
- Installed mod: `%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\Mods\ClaudePlanner\`
- Output: `...\Cities Skylines II\ModsData\ClaudePlanner\plan.html` (and `plan.png`)
- Log: `...\Cities Skylines II\Logs\ClaudePlanner.log`
- **Re-plan without restarting:** create an empty file `replan.txt` in the output folder while the game is running.

To remove the mod, delete the `Mods\ClaudePlanner` folder.

from mcdreforged.api.all import *
from more_command_nodes import Position
import minecraft_data_api as api

psi = ServerInterface.psi()

default_config = {
    "cost": 4
}

def on_load(server: PluginServerInterface, prev_module):
    global config
    server.logger.info("Ender Pearl TP loaded!")
    config = server.load_config_simple('config.json', default_config)
    server.register_command(
        Literal('!!etp')
        .then(
            Literal('Pos')
            .then(
                Position('position')
                .runs(lambda src, ctx: teleport_xyz(src, ctx["position"]))
            )
        )
        .then(
            Text('player')
            .runs(lambda src, ctx: teleport_player(src, ctx["player"]))
        )
    )

def get_info(player: str):
    result = api.get_player_info(player, "Inventory")
    return result

def counter(src):
    player = src.player
    result = get_info(player)
    count_num = sum(item["count"] for item in result if item["id"] == "minecraft:ender_pearl")
    return count_num

def format_position(position: list):
    x = position[0]
    y = position[1]
    z = position[2]
    return f"{x} {y} {z}"

@new_thread('Ender Pearl TP: Teleport xyz')
def teleport_xyz(src: CommandSource, position):
    global config
    if src.is_player:
        player = src.player
        xyz = format_position(position)
        count = counter(src)
        cost = config["cost"]
        if count >= cost:
            psi.execute(f"clear {player} minecraft:ender_pearl {cost}")
            psi.execute(f"tp {player} {xyz}")
            src.reply(f"Teleport to {xyz} successfully, cost {cost} ender pearls.")
        else:
            src.reply(f"Sorry but teleport failed, because you don't have enough ender pearls.")
    else:
        src.reply("Only players online can execute this commmand!")

@new_thread('Ender Pearl TP: Teleport player')
def teleport_player(src: CommandSource, player):
    global config
    if src.is_player:
        executer = src.player
        target_player = player
        count = counter(src)
        cost = config["cost"]
        if count >= cost:
            if executer != target_player:
                psi.execute(f"clear {player} minecraft:ender_pearl {cost}")
                psi.execute(f"tp {executer} {target_player}")
                src.reply(f"Teleport to {target_player} successfully, cost {cost} ender pearls.")
            else:
                src.reply(f"You shouldn't teleport to yourself!")
        else:
            src.reply(f"Sorry but teleport failed, because you don't have enough ender pearls.")

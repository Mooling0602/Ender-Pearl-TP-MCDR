import re

from mcdreforged.api.all import *
from more_command_nodes import Position
import minecraft_data_api as api

psi = ServerInterface.psi()
position_data = {}

default_config = {
    "cost": 4
}

def on_load(server: PluginServerInterface, prev_module):
    global config
    server.logger.info(server.tr("ender_pearl_tp.on_load"))
    config = server.load_config_simple('config.json', default_config)
    server.register_command(
        Literal('!!etp')
        .then(
            Literal('pos')
            .then(
                Position('position')
                .runs(lambda src, ctx: teleport_xyz(src, ctx["position"]))
            )
        )
        .then(
            Literal('back')
            .runs(lambda src: tpback_player(src))
        )
        .then(
            Text('player')
            .runs(lambda src, ctx: teleport_player(src, ctx["player"]))
        )
    )

def get_backpack_info(player: str):
    result: dict = api.get_player_info(player, "Inventory")
    return result

def get_player_pos(player: str):
    global position_data
    result: list = api.get_player_info(player, "Pos")
    position_data[player] = {
        'position': result,
        'allow_back': True
    }

def tpback_player(src: CommandSource):
    global position_data
    player = src.player
    try:
        allow_back = position_data[player]['allow_back']
        if allow_back:
            position = position_data[player]['position']
            xyz = format_position(position)
            psi.execute(f"tp {player} {xyz}")
            position_data[player]['allow_back'] = False
            src.reply(psi.tr("ender_pearl_tp.tp_back.success"))
        else:
            src.reply(psi.tr("ender_pearl_tp.tp_back.failed"))
    except KeyError:
        src.reply(psi.tr("ender_pearl_tp.tp_back.no_data"))

def counter(player: str):
    result = get_backpack_info(player)
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
        count = counter(player)
        cost = config["cost"]
        if count >= cost:
            get_player_pos(player)
            psi.execute(f"tp {player} {xyz}")
            psi.execute(f"clear {player} minecraft:ender_pearl {cost}")
            rest = count - cost
            success_message = psi.tr("ender_pearl_tp.tp_xyz.success").replace("%xyz%", xyz).replace("%cost%", str(cost)).replace("%rest%", str(rest))
            src.reply(success_message)
        else:
            src.reply(psi.tr("ender_pearl_tp.tp_xyz.failed"))
    else:
        src.reply(psi.tr("ender_pearl_tp.no_perm"))

def rcon_online_check(player: str):
    response: str = psi.rcon_query("list")
    match = re.match(r"There are \d+ of a max of \d+ players online:", response)
    if match:
        names_section = response[match.end():].strip()
        online_list = [name.strip() for name in names_section.split(",")]
        if player in online_list:
            return True
        else:
            return False
    else:
        return False

@new_thread('Ender Pearl TP: Teleport player')
def teleport_player(src: CommandSource, player):
    global config
    if src.is_player:
        executer = src.player
        target_player: str = player
        try:
            from online_player_api import check_online # type: ignore
            target_player_status =  check_online(target_player)
            if not target_player_status:
                target_player_status = rcon_online_check(target_player)
        except ModuleNotFoundError:
            target_player_status = rcon_online_check(target_player)
        count = counter(executer)
        cost = config["cost"]
        if count >= cost:
            if executer != target_player:
                if target_player_status:
                    get_player_pos(executer)
                    psi.execute(f"tp {executer} {target_player}")
                    psi.execute(f"clear {executer} minecraft:ender_pearl {cost}")
                    rest = count - cost
                    success_message = psi.tr("ender_pearl_tp.tp_player.success").replace("%target_player%", target_player).replace("%cost%", str(cost)).replace("%rest%", str(rest))
                    src.reply(success_message)
                else:
                    src.reply(psi.tr("ender_pearl_tp.tp_player.failed.reason"))
                    src.reply(psi.tr("ender_pearl_tp.tp_player.failed.result"))
            else:
                src.reply(psi.tr("ender_pearl_tp.tp_player.warning.no_target"))
        else:
            src.reply(psi.tr("ender_pearl_tp.tp_player.warning.cant_cost"))
    else:
        src.reply(psi.tr("ender_pearl_tp.no_perm"))

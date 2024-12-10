import os
import re
import json
import minecraft_data_api as api

from mcdreforged.api.all import *
from more_command_nodes import Position # type: ignore
from .utils import *


position_data = {}
death_back_enabled = False

default_config = {
    "cost": 4,
    "api": {
        "death_back": False
    }
}

api_inject = {
    "api": {
        "enabled": True,
        "register": f"{plgSelf.id}"
    }
}

def api_register(mode):
    if mode == "reg":
        pass
    else:
        api_inject["api"]["enabled"] = False
    os.makedirs("config/death_back", exist_ok=True)
    try:
        with open("config/death_back/api.json", "w", encoding="utf-8") as f:
            json.dump(api_inject, f, )
    except UnicodeEncodeError:
        with open("config/death_back/api.json", "w", encoding="gbk") as f:
            json.dump(api_inject, f, )


def on_load(server: PluginServerInterface, prev_module):
    global config, death_back_enabled
    server.logger.info(tr("on_load"))
    config = server.load_config_simple('config.json', default_config)
    death_back_enabled = config["api"]["death_back"]
    if death_back_enabled:
        api_register("reg")
        server.logger.info(tr("api_registered"))
    else:
        if os.path.exists("config/death_back/api.json"):
            api_register("unreg")
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
            .then(
                Literal('death')
                .runs(lambda src: tpdeath_player(src))
            )
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
    position: list = api.get_player_info(player, "Pos")
    dimension: str = api.get_player_info(player, "Dimension")
    position_data[player] = {
        'position': position,
        'dimension': dimension,
        'allow_back': True
    }

@new_thread("Ender Pearl TP: Teleport back")
def tpback_player(src: CommandSource):
    global position_data
    player = src.player
    try:
        allow_back = position_data[player]['allow_back']
        if allow_back:
            position = position_data[player]['position']
            dimension = position_data[player]['dimension']
            xyz = format_position(position)
            psi.execute(f"execute in {dimension} run tp {player} {xyz}")
            position_data[player]['allow_back'] = False
            src.reply(tr("tp_back.success"))
        else:
            src.reply(tr("tp_back.failed"))
    except KeyError:
        src.reply(tr("tp_back.no_data"))

@new_thread("Ender Pearl TP: Teleport death")
def tpdeath_player(src: CommandSource):
    player = src.player
    count = counter(player)
    cost = config["cost"]
    if death_back_enabled:
        try:
            from death_back import position_data as death_pos
            from packaging.version import Version
            def compare_versions(version1: str, version2: str):
                v1 = Version(str(version1))
                v2 = Version(version2)
                if v1 >= v2:
                    return True
                else:
                    return False
            death_back = psi.get_plugin_metadata("death_back")
            api_ver_match = compare_versions(death_back.version, "0.0.2")
            if api_ver_match:
                if death_pos is not None and death_pos[player] is not None:
                    if count >= cost:
                        position = death_pos[player]['position']
                        dimension = death_pos[player]['dimension']
                        xyz = format_position(position)
                        psi.execute(f"execute in {dimension} run tp {player} {xyz}")
                        psi.execute(f"clear {player} minecraft:ender_pearl {cost}")
                        del death_pos[player]
                        rest = count - cost
                        success_message = tr("tp_death.success").replace("%cost%", str(cost)).replace("%rest%", str(rest))
                        src.reply(success_message)
                    else:
                        src.reply(tr("not_enough"))
                else:
                    src.reply("Error teleport you back: death_back version is too old.")
        except ModuleNotFoundError:
            src.reply(tr("api_not_found"))
        except KeyError:
            src.reply(tr("#death_back.no_data"))
    else:
        src.reply(tr("api_not_enabled"))


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
            success_message = tr("tp_xyz.success").replace("%xyz%", xyz).replace("%cost%", str(cost)).replace("%rest%", str(rest))
            src.reply(success_message)
        else:
            src.reply(tr("not_enough"))
    else:
        src.reply(tr("no_perm"))

def rcon_online_check(player: str):
    response: str = psi.rcon_query("list")
    if response is not None:
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
                    success_message = tr("tp_player.success").replace("%target_player%", target_player).replace("%cost%", str(cost)).replace("%rest%", str(rest))
                    src.reply(success_message)
                else:
                    src.reply(tr("tp_player.failed.reason"))
                    src.reply(tr("tp_player.failed.result"))
            else:
                src.reply(tr("tp_player.warning.no_target"))
        else:
            src.reply(tr("tp_player.not_enough"))
    else:
        src.reply(tr("ender_pearl_tp.no_perm"))

try:
    import ujson as json
except ImportError:
    import json
import os
from pathlib import Path
from typing import Any, Tuple
from nonebot import on_regex
from nonebot.log import logger
from nonebot.params import RegexGroup
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    GROUP,
    MessageSegment,
)
from ..xiuxian_utils.lay_out import Cooldown
from ..xiuxian_utils.xiuxian2_handle import sql_message
from datetime import datetime
from .bankconfig import CONFIG
from ..xiuxian_utils.utils import check_user, get_msg_pic, number_to
from ..xiuxian_config import XiuConfig

config = CONFIG
BANKLEVEL = config["BANKLEVEL"]
PLAYERSDATA = Path() / "data" / "xiuxian" / "players"

bank = on_regex(
    r'^灵庄(存灵石|取灵石|升级会员|信息|结算)?(.*)?',
    priority=9,
    permission=GROUP,
    block=True
)

__bank_help__ = f"""
灵庄帮助信息:
指令：
1：灵庄
 - 查看灵庄帮助信息
2：灵庄存灵石
 - 指令后加存入的金额,获取利息
3：灵庄取灵石
 - 指令后加取出的金额,会先结算利息,再取出灵石
4：灵庄升级会员
 - 灵庄利息倍率与灵庄会员等级有关,升级会员会提升利息倍率
5：灵庄信息
 - 查询自己当前的灵庄信息
6：灵庄结算
 - 结算利息
——tips——
官方群914556251
""".strip()


@bank.handle(parameterless=[Cooldown(at_sender=False)])
async def bank_(bot: Bot, event: GroupMessageEvent, args: Tuple[Any, ...] = RegexGroup()):
    isUser, user_info, msg = await check_user(event)
    mode = args[0]  # 存灵石、取灵石、升级会员、信息查看
    num = args[1]  # 数值
    if mode is None:
        msg = __bank_help__
        await bot.send(event=event, message=msg)
        await bank.finish()

    if mode == '存灵石' or mode == '取灵石':
        try:
            num = int(num)
            if num <= 0:
                msg = f"请输入正确的金额！"
                await bot.send(event=event, message=msg)
                await bank.finish()
        except ValueError:
            msg = f"请输入正确的金额！"
            await bot.send(event=event, message=msg)
            await bank.finish()
    user_id = user_info['user_id']
    try:
        bankinfo = readf(user_id)
    except:
        bankinfo = {
            'savestone': 0,
            'savetime': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'banklevel': '1',
        }

    if mode == '存灵石':  # 存灵石逻辑
        if int(user_info['stone']) < num:
            msg = (f"道友所拥有的灵石为{number_to(user_info['stone'])}|{user_info['stone']}枚，"
                   f"金额不足，请重新输入！")
            await bot.send(event=event, message=msg)
            await bank.finish()

        max = BANKLEVEL[bankinfo['banklevel']]['savemax']
        nowmax = max - bankinfo['savestone']

        if num > nowmax:
            msg = (f"道友当前灵庄会员等级为{BANKLEVEL[bankinfo['banklevel']]['level']}，"
                   f"可存储的最大灵石为{number_to(max)}|{max}枚,"
                   f"当前已存{number_to(bankinfo['savestone'])}|{bankinfo['savestone']}枚灵石，"
                   f"可以继续存{number_to(nowmax)}|{nowmax}枚灵石！")
            await bot.send(event=event, message=msg)
            await bank.finish()

        bankinfo, give_stone, timedeff = get_give_stone(bankinfo)
        userinfonowstone = int(user_info['stone']) - num
        bankinfo['savestone'] += num
        await sql_message.update_ls(user_id, num, 2)
        await sql_message.update_ls(user_id, give_stone, 1)
        bankinfo['savetime'] = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        savef(user_id, bankinfo)
        msg = (f"道友本次结息时间为：{timedeff}小时，"
               f"获得灵石：{number_to(give_stone)}|{give_stone}枚!\r"
               f"道友存入灵石{number_to(num)}|{num}枚，"
               f"当前所拥有灵石{number_to(userinfonowstone + give_stone)}|{userinfonowstone + give_stone}枚，"
               f"灵庄存有灵石{number_to(bankinfo['savestone'])}|{bankinfo['savestone']}枚")
        await bot.send(event=event, message=msg)
        await bank.finish()

    elif mode == '取灵石':  # 取灵石逻辑
        if int(bankinfo['savestone']) < num:
            msg = f"道友当前灵庄所存有的灵石为{number_to(bankinfo['savestone'])}|{bankinfo['savestone']}枚，金额不足，请重新输入！"
            await bot.send(event=event, message=msg)
            await bank.finish()

        # 先结算利息
        bankinfo, give_stone, timedeff = get_give_stone(bankinfo)

        userinfonowstone = int(user_info['stone']) + num + give_stone
        bankinfo['savestone'] -= num
        await sql_message.update_ls(user_id, num + give_stone, 1)
        savef(user_id, bankinfo)
        msg = (f"道友本次结息时间为：{timedeff}小时，获得灵石：{number_to(give_stone)}|{give_stone}枚!\r"
               f"取出灵石{number_to(num)}|{num}枚，当前所拥有灵石{number_to(userinfonowstone)}|{userinfonowstone}枚，"
               f"灵庄存有灵石{number_to(bankinfo['savestone'])}|{bankinfo['savestone']}枚!")
        await bot.send(event=event, message=msg)
        await bank.finish()

    elif mode == '升级会员':  # 升级会员逻辑
        userlevel = bankinfo["banklevel"]
        if int(userlevel) == int(len(BANKLEVEL)) - 1:
            msg = f"灵庄分庄已被不知名道友提前建设！"
            await bot.send(event=event, message=msg)
            await bank.finish()

        if userlevel == str(len(BANKLEVEL)):
            msg = f"道友已经是本灵庄最大的会员啦！"
            await bot.send(event=event, message=msg)
            await bank.finish()
        stonecost = BANKLEVEL[f"{int(userlevel)}"]['levelup']
        if int(user_info['stone']) < stonecost:
            msg = (f"道友所拥有的灵石为{number_to(user_info['stone'])}|{user_info['stone']}枚，"
                   f"当前升级会员等级需求灵石{number_to(stonecost)}|{stonecost}枚金额不足，请重新输入！")
            await bot.send(event=event, message=msg)
            await bank.finish()

        await sql_message.update_ls(user_id, stonecost, 2)
        bankinfo['banklevel'] = f"{int(userlevel) + 1}"
        savef(user_id, bankinfo)
        msg = (f"道友成功升级灵庄会员等级，消耗灵石{number_to(stonecost)}|{stonecost}枚，"
               f"当前为：{BANKLEVEL[str(int(userlevel) + 1)]['level']}，"
               f"灵庄可存有灵石上限{number_to(BANKLEVEL[str(int(userlevel) + 1)]['savemax'])}"
               f"|{BANKLEVEL[str(int(userlevel) + 1)]['savemax']}枚")

        await bot.send(event=event, message=msg)
        await bank.finish()

    elif mode == '信息':  # 查询灵庄信息
        msg = f'''道友的灵庄信息：
已存：{number_to(bankinfo['savestone'])}|{bankinfo['savestone']}灵石
存入时间：{bankinfo['savetime']}
灵庄会员等级：{BANKLEVEL[bankinfo['banklevel']]['level']}
当前拥有灵石：{number_to(user_info['stone'])}|{user_info['stone']}
当前等级存储灵石上限：{BANKLEVEL[bankinfo['banklevel']]['savemax']}枚
'''
        await bot.send(event=event, message=msg)
        await bank.finish()

    elif mode == '结算':

        bankinfo, give_stone, timedeff = get_give_stone(bankinfo)
        await sql_message.update_ls(user_id, give_stone, 1)
        savef(user_id, bankinfo)
        msg = f"道友本次结息时间为：{timedeff}小时，获得灵石：{number_to(give_stone)}|{give_stone}枚！"
        await bot.send(event=event, message=msg)
        await bank.finish()


def get_give_stone(bankinfo):
    """获取利息：利息=give_stone,结算时间=timedeff"""
    savetime = bankinfo['savetime']  # str
    nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # str
    timedeff = round((datetime.strptime(nowtime, '%Y-%m-%d %H:%M:%S') -
                      datetime.strptime(savetime, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600, 2)
    give_stone = int(bankinfo['savestone'] * timedeff * BANKLEVEL[bankinfo['banklevel']]['interest'])
    bankinfo['savetime'] = nowtime

    return bankinfo, give_stone, timedeff


def readf(user_id):
    # 万恶的json，灵庄部分，迟早清算你
    user_id = str(user_id)
    FILEPATH = PLAYERSDATA / user_id / "bankinfo.json"
    with open(FILEPATH, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)


def savef(user_id, data):
    user_id = str(user_id)
    if not os.path.exists(PLAYERSDATA / user_id):
        logger.opt(colors=True).info(f"<green>用户目录不存在，创建目录</green>")
        os.makedirs(PLAYERSDATA / user_id)
    FILEPATH = PLAYERSDATA / user_id / "bankinfo.json"
    data = json.dumps(data, ensure_ascii=False, indent=3)
    savemode = "w" if os.path.exists(FILEPATH) else "x"
    with open(FILEPATH, mode=savemode, encoding="UTF-8") as f:
        f.write(data)
        f.close()
    return True

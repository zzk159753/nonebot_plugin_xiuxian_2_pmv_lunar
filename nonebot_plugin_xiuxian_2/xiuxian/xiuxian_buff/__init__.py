import random
import re
from datetime import datetime

from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent
)
from nonebot.params import CommandArg, RawCommand
from nonebot.permission import SUPERUSER

from .limit import check_limit, reset_send_stone, reset_stone_exp_up
from .two_exp_cd import two_exp_cd
from ..user_data_handle import UserBuffHandle
from ..user_data_handle.fight.fight_pvp import player_fight
from ..world_boss.world_boss_database import get_user_world_boss_info
from ..xiuxian_config import XiuConfig
from ..xiuxian_data.data.境界_data import level_data
from ..xiuxian_data.data.突破概率_data import break_rate
from ..xiuxian_database.database_connect import database
from ..xiuxian_exp_up.exp_up_def import exp_up_by_time
from ..xiuxian_impart_pk import impart_pk_check
from ..xiuxian_limit.limit_database import limit_handle, limit_data
from ..xiuxian_limit.limit_util import limit_check
from ..xiuxian_mixelixir.mix_elixir_database import get_user_mix_elixir_info
from ..xiuxian_place import place
from ..xiuxian_tower import tower_handle
from ..xiuxian_utils.clean_utils import (get_datetime_from_str,
                                         date_sub, main_md,
                                         simple_md, get_args_num)
from ..xiuxian_utils.lay_out import Cooldown
from ..xiuxian_utils.other_set import OtherSet
from ..xiuxian_utils.utils import (
    number_to, check_user,
    check_user_type, get_id_from_str
)
from ..xiuxian_utils.xiuxian2_handle import (
    sql_message, UserBuffDate, get_main_info_msg,
    get_user_buff, get_sec_msg, get_sub_info_msg,
    xiuxian_impart
)

cache_help = {}
BLESSEDSPOTCOST = 3500000
two_exp_limit = XiuConfig().two_exp_limit  # 默认双修次数上限，修仙之人一天7次也不奇怪（

buffinfo = on_command("我的功法", priority=1, permission=GROUP, block=True)
out_closing = on_command("出关", aliases={"灵石出关"}, priority=5, permission=GROUP, block=True)
in_closing = on_command("闭关", priority=5, permission=GROUP, block=True)
stone_exp = on_command("灵石修仙", aliases={"灵石修炼", "/灵石修炼"}, priority=1, permission=GROUP, block=True)
two_exp = on_command("双修", aliases={"快速双修", "确认快速双修"}, priority=5, permission=GROUP, block=True)
send_exp = on_command("传道", aliases={"传法", "指点"}, priority=5, permission=GROUP, block=True)
mind_state = on_command("我的状态", aliases={"/我的状态"}, priority=2, permission=GROUP, block=True)
select_state = on_command("查看状态", aliases={"查状态"}, priority=2, permission=GROUP, block=True)
qc = on_command("切磋", priority=6, permission=GROUP, block=True)
blessed_spot_create = on_command("洞天福地购买", aliases={"获取洞天福地", "购买洞天福地"}, priority=1, permission=GROUP,
                                 block=True)
blessed_spot_info = on_command("洞天福地查看", aliases={"我的洞天福地", "查看洞天福地"}, priority=1, permission=GROUP,
                               block=True)
blessed_spot_rename = on_command("洞天福地改名", aliases={"改名洞天福地", "改洞天福地名"}, priority=1, permission=GROUP,
                                 block=True)
ling_tian_up = on_command("灵田开垦", priority=5, permission=GROUP, block=True)
del_exp_decimal = on_command("抑制黑暗动乱", priority=9, permission=GROUP, block=True)
my_exp_num = on_command("我的双修次数", priority=9, permission=GROUP, block=True)
a_test = on_command("测试保存", priority=9, permission=SUPERUSER, block=True)
daily_work = on_command("日常", priority=9, permission=GROUP, block=True)


@blessed_spot_create.handle(parameterless=[Cooldown()])
async def blessed_spot_create_(bot: Bot, event: GroupMessageEvent):
    """洞天福地购买"""
    user_info = await check_user(event)

    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) != 0:
        msg = f"道友已经拥有洞天福地了，请发送洞天福地查看吧~"
        await bot.send(event=event, message=msg)
        await blessed_spot_create.finish()
    if user_info['stone'] < BLESSEDSPOTCOST:
        msg = f"道友的灵石不足{BLESSEDSPOTCOST}枚，无法购买洞天福地"
        await bot.send(event=event, message=msg)
        await blessed_spot_create.finish()
    else:
        await sql_message.update_ls(user_id, BLESSEDSPOTCOST, 2)
        await sql_message.update_user_blessed_spot_flag(user_id)
        await get_user_mix_elixir_info(user_id)
        update_mix_elixir_info = {'farm_harvest_time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                                  'farm_num': 1}
        await database.update(table='mix_elixir_info',
                              where={'user_id': user_id},
                              **update_mix_elixir_info)
        msg = f"恭喜道友拥有了自己的洞天福地，请收集聚灵旗来提升洞天福地的等级吧~\r"
        msg += f"默认名称为：{user_info['user_name']}道友的家"
        await sql_message.update_user_blessed_spot_name(user_id, f"{user_info['user_name']}道友的家")
        await bot.send(event=event, message=msg)
        await blessed_spot_create.finish()


@blessed_spot_info.handle(parameterless=[Cooldown()])
async def blessed_spot_info_(bot: Bot, event: GroupMessageEvent):
    """洞天福地信息"""
    user_info = await check_user(event)

    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买来购买吧~"
        await bot.send(event=event, message=msg)
        await blessed_spot_info.finish()
    msg = f"\r道友的洞天福地:\r"
    user_buff_data = await UserBuffDate(user_id).buff_info
    if user_info['blessed_spot_name'] == 0:
        blessed_spot_name = "尚未命名"
    else:
        blessed_spot_name = user_info['blessed_spot_name']
    mix_elixir_info = await get_user_mix_elixir_info(user_id)
    msg += f"名字：{blessed_spot_name}\r"
    msg += f"聚灵旗：{user_buff_data['blessed_spot_name']}\r"
    msg += f"修炼速度：增加{user_buff_data['blessed_spot'] * 100:.2f}%\r"
    msg += f"灵田数量：{mix_elixir_info['farm_num']}"
    await bot.send(event=event, message=msg)
    await blessed_spot_info.finish()


@ling_tian_up.handle(parameterless=[Cooldown()])
async def ling_tian_up_(bot: Bot, event: GroupMessageEvent):
    """洞天福地灵田升级"""
    # 这里曾经是风控模块，但是已经不再需要了
    user_info = await check_user(event)

    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await bot.send(event=event, message=msg)
        await ling_tian_up.finish()
    LINGTIANCONFIG = {
        "1": {
            "level_up_cost": 3500000
        },
        "2": {
            "level_up_cost": 5000000
        },
        "3": {
            "level_up_cost": 7000000
        },
        "4": {
            "level_up_cost": 10000000
        },
        "5": {
            "level_up_cost": 15000000
        },
        "6": {
            "level_up_cost": 30000000
        },
        "7": {
            "level_up_cost": 90000000
        },
        "8": {
            "level_up_cost": 150000000
        },
        "9": {
            "level_up_cost": 300000000
        },
        "10": {
            "level_up_cost": 600000000
        },
        "11": {
            "level_up_cost": 1000000000
        },
        "12": {
            "level_up_cost": 2000000000
        },
        "13": {
            "level_up_cost": 3000000000
        },
        "14": {
            "level_up_cost": 4000000000
        }
    }
    mix_elixir_info = await get_user_mix_elixir_info(user_id)
    now_num = mix_elixir_info['farm_num']
    if now_num == len(LINGTIANCONFIG) + 1:
        msg = f"道友的灵田已全部开垦完毕，无法继续开垦了！"
    else:
        cost = LINGTIANCONFIG[str(now_num)]['level_up_cost']
        if int(user_info['stone']) < cost:
            msg = f"本次开垦需要灵石：{cost}，道友的灵石不足！"
        else:
            msg = f"道友成功消耗灵石：{cost}，灵田数量+1,目前数量:{now_num + 1}"
            update_mix_elixir_info = {'farm_num': now_num + 1}
            await database.update(table='mix_elixir_info',
                                  where={'user_id': user_id},
                                  **update_mix_elixir_info)
            await sql_message.update_ls(user_id, cost, 2)
    await bot.send(event=event, message=msg)
    await ling_tian_up.finish()


@blessed_spot_rename.handle(parameterless=[Cooldown()])
async def blessed_spot_rename_(bot: Bot, event: GroupMessageEvent):
    """洞天福地改名"""
    # 这里曾经是风控模块，但是已经不再需要了
    user_info = await check_user(event)

    user_id = user_info['user_id']
    if int(user_info['blessed_spot_flag']) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await bot.send(event=event, message=msg)
        await blessed_spot_rename.finish()
    blessed_spot_name_list = ("霍桐山洞，东岳泰山洞，南岳衡山洞，西岳华山洞，北岳常山洞，中岳嵩山洞，峨嵋山洞，庐山洞，四明山洞，会稽山洞，"
                              "太白山洞，西山洞，小沩山洞，火氓山洞，鬼谷山洞，武夷山洞，玉笥山洞，华盖山洞，盖竹山洞，都峤山洞，白石山洞，"
                              "岣嵝山洞，九嶷山洞，洞阳山洞，幕阜山洞，大酉山洞，金庭山洞，麻 姑山洞，仙都山洞，青田山洞，钟山洞，良常山洞，"
                              "紫山洞，天目山洞，桃源山洞，金华山洞，地肺山，盖竹山，仙磕山，东仙源，西仙源，南田山，玉溜山，清屿山，郁木洞，"
                              "丹霞洞，君山，大若岩，焦源，灵墟，沃洲，天姥岭，若耶溪，金庭山，清远山，安山，马岭山，鹅羊山，洞真墟，青玉坛，"
                              "光天坛，洞灵源，洞宫山，陶山，三皇井 ，烂柯山，勒溪，龙虎山，灵山，泉源，金精山，阁皂山，始丰山，逍遥山，东白源，"
                              "钵池山，论山，毛公坛，鸡笼山，桐柏山，平都山，绿萝山，虎溪山，彰龙山，抱福山，大面山，元晨山，马蹄山，德山，高溪山，"
                              "蓝水，玉峰，天柱山，商谷山，张公洞，司马悔山，长在山，中条山，茭湖鱼澄洞，绵竹山，泸水，甘山，莫寻山，金城山，云山，"
                              "北邙山，卢山，东海山").split("，")
    arg = random.choice(blessed_spot_name_list)
    msg = f"道友的洞天福地成功改名为：{arg}"
    await sql_message.update_user_blessed_spot_name(user_id, arg)
    await bot.send(event=event, message=msg)
    await blessed_spot_rename.finish()


@qc.handle(parameterless=[Cooldown(cd_time=20)])
async def qc_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """切磋，不会掉血"""

    args = args.extract_plain_text()
    give_qq = await get_id_from_str(args)  # 使用道号获取用户id，代替原at

    user_info = await check_user(event)

    user_id = user_info['user_id']

    user1 = await sql_message.get_user_real_info(user_id)
    user2 = await sql_message.get_user_real_info(give_qq)
    if give_qq:
        if give_qq == user_id:
            msg = "道友不会左右互搏之术！"
            await bot.send(event=event, message=msg)
            await qc.finish()

    if user1 and user2:
        victor, text = await player_fight({user_id: 1, give_qq: 2})
        msg = f"新战斗测试中，获胜的是{victor}"
        msg = main_md(msg, text, '切磋其他人', '切磋', '修炼', '修炼', '闭关', '闭关', '修仙帮助', '修仙帮助')
        await bot.send(event=event, message=msg)
        await qc.finish()
    else:
        msg = "修仙界没有对方的信息，快邀请对方加入修仙界吧！"
        await bot.send(event=event, message=msg)
        await qc.finish()


@send_exp.handle(parameterless=[Cooldown(cd_time=3, stamina_cost=0)])
async def send_exp_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """双修"""

    user_1 = await check_user(event)

    args = args.extract_plain_text()

    user_1_id = user_1['user_id']
    user_2_id = await get_id_from_str(args)  # 使用道号获取用户id，代替原at

    user_2 = await sql_message.get_user_info_with_id(user_2_id)

    num = get_args_num(args=args, no=1, default=1)
    num = 1 if num == 0 else num

    if num > 30:
        msg = "道友没有那么闲情逸致连续指点那么多次！"
        await bot.send(event=event, message=msg)
        await send_exp.finish()

    if not user_2_id:
        msg = "请输入你要传道者的道号,为其开悟，彻明万道！"
        await bot.send(event=event, message=msg)
        await send_exp.finish()

    if int(user_1_id) == int(user_2_id):
        msg = "道友无法指点自己！"
        await bot.send(event=event, message=msg)
        await send_exp.finish()

    exp_1 = user_1['exp']
    exp_2 = user_2['exp']
    if exp_2 > exp_1:
        msg = "修仙大能看了看你，不屑一顾，扬长而去！"
        await bot.send(event=event, message=msg)
        await send_exp.finish()

    is_type, msg = await check_user_type(user_2_id, 0)
    if user_2['root_type'] in ['源宇道根', '道之本源']:
        msg = "对方已得悟大道，无需道友指点！！"
        await bot.send(event=event, message=msg)
        await send_exp.finish()
    if exp_2 > 18e10:
        msg = "对方对修炼已颇有见解，无需道友指点！！"
        await bot.send(event=event, message=msg)
        await send_exp.finish()
    if not is_type:
        msg = "对方正在忙碌中，暂时无法蒙受道友恩惠！！"
        await bot.send(event=event, message=msg)
        await send_exp.finish()
    exp = int(exp_1 * 0.0055)
    max_exp = XiuConfig().two_exp  # 双修上限罪魁祸首
    if user_1['root_type'] in ['源宇道根', '道之本源']:
        exp = max_exp
    if exp < max_exp:
        msg = "道友正欲指点对方一番，奈何道友尚无深悟，难以指点！！"
        await bot.send(event=event, message=msg)
        await send_exp.finish()

    # 获取下个境界需要的修为 * 1.5为闭关上限
    max_exp_2 = (int(await OtherSet().set_closing_type(user_2['level']))
                 * XiuConfig().closing_exp_upper_limit)
    user_get_exp_max_2 = max(max_exp_2 - user_2['exp'], 0)
    if not user_get_exp_max_2:
        msg = "对方修为已达上限！！"
        await bot.send(event=event, message=msg)
        await send_exp.finish()

    msg = f"{user_1['user_name']}道友见{user_2['user_name']}道友颇有道缘，指点一番。"
    # 玩家2修为增加
    exp_limit_2 = min(exp, max_exp)

    # 玩家2修为上限
    if exp_limit_2 * num >= user_get_exp_max_2:
        msg += f"{user_2['user_name']}修为将到达上限，仅可指点1次！\r"
        num = 1
    exp_limit_2 *= num

    is_pass, is_pass_msg = await limit_check.send_exp_limit_check(user_id_2=user_2_id, num=num)
    if not is_pass:
        await bot.send(event=event, message=is_pass_msg)
        await send_exp.finish()

    # 玩家2修为上限
    if exp_limit_2 >= user_get_exp_max_2:
        await sql_message.update_exp(user_2_id, user_get_exp_max_2)
        msg += f"{user_2['user_name']}修为到达上限，增加修为{user_get_exp_max_2}。"
    else:
        await sql_message.update_exp(user_2_id, exp_limit_2)
        msg += f"{user_2['user_name']}增加修为{exp_limit_2}。"

    # 双修彩蛋，突破概率增加
    break_rate_up = 0
    for _ in range(num):
        if random.randint(1, 100) in [13, 14, 52, 10, 66]:
            break_rate_up += 2
    if break_rate_up:
        await sql_message.update_levelrate(user_2_id, user_2['level_up_rate'] + break_rate_up)
        msg += f"\r道友舌灿莲花，言蕴大道，对方感悟颇丰突破概率提升{break_rate_up}%。"
    await sql_message.update_power2(user_2_id)
    await limit_handle.update_user_log_data(user_1_id, msg)
    await limit_handle.update_user_log_data(user_2_id, msg)
    msg = main_md(
        "信息", msg,
        '查看日常', "日常中心",
        '指点', '指点',
        '修炼', '修炼',
        '继续指点', f"指点{user_2['user_name']} {num}")
    await bot.send(event=event, message=msg)
    await send_exp.finish()


@two_exp.handle(parameterless=[Cooldown(stamina_cost=0)])
async def two_exp_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg(), cmd: str = RawCommand()):
    """双修"""

    user_1 = await check_user(event)

    args = args.extract_plain_text()

    user_1_id = user_1['user_id']
    user_2_id = await get_id_from_str(args)  # 使用道号获取用户id，代替原at

    user_2 = await sql_message.get_user_info_with_id(user_2_id)

    num = get_args_num(args=args, no=1, default=1)
    num = 1 if num == 0 else num
    if not user_2_id:
        msg = "请输入你道侣的道号,与其一起双修！"
        await bot.send(event=event, message=msg)
        await two_exp.finish()

    if int(user_1_id) == int(user_2_id):
        msg = "道友无法与自己双修！"
        await bot.send(event=event, message=msg)
        await two_exp.finish()

    exp_1 = user_1['exp']
    exp_2 = user_2['exp']
    if exp_2 > exp_1:
        msg = "修仙大能看了看你，不屑一顾，扬长而去！"
        await bot.send(event=event, message=msg)
        await two_exp.finish()

    if await place.is_the_same_place(int(user_1_id), int(user_2_id)) is False:
        msg = "道友与你的道侣不在同一位置，请邀约道侣前来双修！！！"
        await bot.send(event=event, message=msg)
        await two_exp.finish()

    is_type, msg = await check_user_type(user_2_id, 0)
    if not is_type:
        msg = "对方正在忙碌中，暂时无法与道友双修！！"
        await bot.send(event=event, message=msg)
        await two_exp.finish()

    # 获取下个境界需要的修为 * 1.5为闭关上限
    max_exp_1 = (int(await OtherSet().set_closing_type(user_1['level']))
                 * XiuConfig().closing_exp_upper_limit)
    max_exp_2 = (int(await OtherSet().set_closing_type(user_2['level']))
                 * XiuConfig().closing_exp_upper_limit)
    user_get_exp_max_1 = max(max_exp_1 - user_1['exp'], 0)
    user_get_exp_max_2 = max(max_exp_2 - user_2['exp'], 0)
    if (not user_get_exp_max_2) and user_2['user_name'] not in ['凌云', '凌云三']:
        msg = "对方修为已达上限！！"
        await bot.send(event=event, message=msg)
        await send_exp.finish()

    msg = f"{user_1['user_name']}与{user_2['user_name']}情投意合，于某地一起修炼了一晚。"
    exp = int((exp_1 + exp_2) * 0.0055)
    max_exp = XiuConfig().two_exp  # 双修上限罪魁祸首
    # 玩家1修为增加
    if exp >= max_exp:
        if user_1['root_type'] not in ['源宇道根', '道之本源']:
            exp_limit_1 = max_exp
        else:
            exp_limit_1 = max_exp * 10
    else:
        exp_limit_1 = exp
    # 玩家2修为增加
    if exp >= max_exp:
        if user_2['root_type'] not in ['源宇道根', '道之本源']:
            exp_limit_2 = max_exp
        else:
            exp_limit_2 = max_exp * 10
    else:
        exp_limit_2 = exp
    # 玩家2修为上限
    if (exp_limit_2 * num >= user_get_exp_max_2) and user_2['user_name'] not in ['凌云', '凌云三']:
        msg += f"{user_2['user_name']}修为将到达上限，仅可双修1次！\r"
        num = 1

    exp_limit_1 *= num
    exp_limit_2 *= num

    is_pass, pass_msg = await limit_check.two_exp_limit_check(user_id_1=user_1_id, user_id_2=user_2_id, num=num)
    if not is_pass:
        await bot.send(event=event, message=pass_msg)
        await two_exp.finish()

    # 玩家1修为上限
    if exp_limit_1 >= user_get_exp_max_1:
        await sql_message.update_exp(user_1_id, user_get_exp_max_1)
        msg += f"{user_1['user_name']}修为到达上限，增加修为{user_get_exp_max_1}。"
    else:
        await sql_message.update_exp(user_1_id, exp_limit_1)
        msg += f"{user_1['user_name']}增加修为{exp_limit_1}。"

    # 玩家2修为上限
    if exp_limit_2 >= user_get_exp_max_2:
        await sql_message.update_exp(user_2_id, user_get_exp_max_2)
        msg += f"{user_2['user_name']}修为到达上限，增加修为{user_get_exp_max_2}。"
    else:
        await sql_message.update_exp(user_2_id, exp_limit_2)
        msg += f"{user_2['user_name']}增加修为{exp_limit_2}。"

    # 双修彩蛋，突破概率增加
    break_rate_up = 0
    for _ in range(num):
        if random.randint(1, 100) in [13, 14, 52, 10, 66]:
            break_rate_up += 2
    if break_rate_up:
        await sql_message.update_levelrate(user_1_id, user_1['level_up_rate'] + break_rate_up)
        await sql_message.update_levelrate(user_2_id, user_2['level_up_rate'] + break_rate_up)
        msg += f"离开时双方互相留法宝为对方护道,双方各增加突破概率{break_rate_up}%。"
    await sql_message.update_power2(user_1_id)
    await sql_message.update_power2(user_2_id)
    await limit_handle.update_user_log_data(user_1_id, msg)
    await limit_handle.update_user_log_data(user_2_id, msg)
    msg = main_md(
        "信息", msg,
        '查看日常', "日常中心",
        '双修', '双修',
        '修炼', '修炼',
        '继续双修', f"双修{user_2['user_name']} {num}")
    await bot.send(event=event, message=msg)
    await two_exp.finish()


@stone_exp.handle(parameterless=[Cooldown()])
async def stone_exp_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """灵石修炼"""

    user_info = await check_user(event)

    user_id = user_info['user_id']
    user_mes = await sql_message.get_user_info_with_id(user_id)  # 获取用户信息
    level = user_mes['level']
    use_exp = user_mes['exp']
    use_stone = user_mes['stone']
    max_exp = (
            int(await OtherSet().set_closing_type(level)) * XiuConfig().closing_exp_upper_limit
    )  # 获取下个境界需要的修为 * 1.5为闭关上限
    user_get_exp_max = int(max_exp) - use_exp

    if user_get_exp_max < 0:
        # 校验当当前修为超出上限的问题，不可为负数
        user_get_exp_max = 0

    msg = args.extract_plain_text().strip()
    stone_num = re.findall(r"\d+", msg)  # 灵石数

    if stone_num:
        pass
    else:
        msg = "请输入正确的灵石数量！"
        await bot.send(event=event, message=msg)
        await stone_exp.finish()

    stone_num = int(stone_num[0])

    if use_stone <= stone_num:
        msg = "你的灵石还不够呢，快去赚点灵石吧！"
        await bot.send(event=event, message=msg)
        await stone_exp.finish()

    exp = int(stone_num / 10)
    if exp >= user_get_exp_max:
        # 用户获取的修为到达上限
        stone_num = user_get_exp_max * 10
        exp = int(stone_num / 10)
        num, msg, is_pass = await check_limit.stone_exp_up_check(user_id, stone_num)
        if is_pass:
            await sql_message.update_exp(user_id, exp)
            await sql_message.update_power2(user_id)  # 更新战力
            msg = (f"修炼结束，本次修炼到达上限，共增加修为：{number_to(exp)}|{exp},"
                   f"消耗灵石：{number_to(stone_num)}|{stone_num}") + msg
            await sql_message.update_ls(user_id, int(stone_num), 2)
            await bot.send(event=event, message=msg)
            await stone_exp.finish()
        else:
            await bot.send(event=event, message=msg)
            await stone_exp.finish()
    else:
        num, msg, is_pass = await check_limit.stone_exp_up_check(user_id, stone_num)
        if is_pass:
            await sql_message.update_exp(user_id, exp)
            await sql_message.update_power2(user_id)  # 更新战力
            msg = (f"修炼结束，本次修炼共增加修为：{number_to(exp)}|{exp},"
                   f"消耗灵石：{number_to(stone_num)}|{stone_num}") + msg
            await sql_message.update_ls(user_id, int(stone_num), 2)
            await bot.send(event=event, message=msg)
            await stone_exp.finish()
        else:
            await bot.send(event=event, message=msg)
            await stone_exp.finish()


@in_closing.handle(parameterless=[Cooldown()])
async def in_closing_(bot: Bot, event: GroupMessageEvent):
    """闭关"""
    user_type = 1  # 状态1为闭关状态

    user_info = await check_user(event)

    user_id = user_info['user_id']
    is_type, msg = await check_user_type(user_id, 0)
    if is_type:  # 符合
        await sql_message.in_closing(user_id, user_type)
        msg = simple_md('进入闭关状态如需出关，发送', '出关', "出关", '！')
    await bot.send(event=event, message=msg)
    await in_closing.finish()


@out_closing.handle(parameterless=[Cooldown()])
async def out_closing_(bot: Bot, event: GroupMessageEvent):
    """出关"""
    # 状态变更事件标识
    user_type = 0  # 状态0为无事件
    # 获取用户信息
    user_info = await check_user(event)
    # 获取用户id
    user_id = user_info['user_id']

    now_time = datetime.now()
    is_type, msg = await check_user_type(user_id, 1)
    is_xu_world_type, msg = await check_user_type(user_id, 5)
    if is_type or is_xu_world_type:
        # 进入闭关的时间
        user_cd_message = await sql_message.get_user_cd(user_id)
        in_closing_time = get_datetime_from_str(user_cd_message['create_time'])

        # 闭关时长计算(分钟) = second // 60
        time_diff = date_sub(now_time, in_closing_time)
        exp_time = time_diff // 60
        close_time = exp_time
        # 用户状态检测，是否在虚神界闭关中
        if is_xu_world_type:
            # 虚神界闭关时长计算
            impart_data_draw = await impart_pk_check(user_id)
            impart_exp_time = int(impart_data_draw['exp_day'])
            # 余剩时间
            last_time = max(impart_exp_time - exp_time, 0)
            is_xu_world = '虚神界'
            # 余剩时间检测
            if last_time:
                await xiuxian_impart.use_impart_exp_day(exp_time, user_id)
                exp_time = exp_time * 6
                time_tipe = ''
            else:
                await xiuxian_impart.use_impart_exp_day(impart_exp_time, user_id)
                exp_time = exp_time + impart_exp_time * 5
                time_tipe = '耗尽'
            time_msg = f"{time_tipe}余剩虚神界内闭关时间：{last_time}分钟，"
        else:
            is_xu_world = ''
            time_msg = ''

        # 退出状态
        await sql_message.in_closing(user_id, user_type)
        # 根据时间发送修为
        is_full, exp, result_msg = await exp_up_by_time(user_info, exp_time)
        # 拼接提示
        msg = (f"{is_xu_world}闭关修炼结束，{is_full}共闭关{close_time}分钟，{time_msg}"
               f"本次闭关共增加修为：{number_to(exp)}|{exp}{result_msg[0]}{result_msg[1]}")
        msg = main_md(
            msg, str(now_time),
            '修炼', '修炼',
            '闭关', '闭关',
            '虚神界闭关', '虚神界闭关',
            '修仙帮助', '修仙帮助')
    await bot.send(event=event, message=msg)
    await out_closing.finish()


@mind_state.handle(parameterless=[Cooldown()])
async def mind_state_(bot: Bot, event: GroupMessageEvent):
    """我的状态信息"""

    user_info = await check_user(event)

    user_id = user_info['user_id']
    await sql_message.update_last_check_info_time(user_id)  # 更新查看修仙信息时间
    if user_info['hp'] is None or user_info['hp'] == 0:
        await sql_message.update_user_hp(user_id)
    user_buff_handle = UserBuffHandle(user_id)
    user_fight_info, user_buff_info = await user_buff_handle.get_user_fight_info_with_buff_info()
    level_rate = await sql_message.get_root_rate(user_fight_info['root_type'])  # 灵根倍率
    realm_rate = level_data[user_fight_info['level']]["spend"]  # 境界倍率

    # 突破状态
    list_all = len(OtherSet().level) - 1
    now_index = OtherSet().level.index(user_info['level'])
    if list_all == now_index:
        exp_meg = f"位面至高"
    else:
        is_updata_level = OtherSet().level[now_index + 1]
        need_exp = await sql_message.get_level_power(is_updata_level)
        get_exp = need_exp - user_info['exp']
        if get_exp > 0:
            exp_meg = f"还需{number_to(get_exp)}修为可突破！"
        else:
            exp_meg = f"可突破！"

    # 主功法突破概率提升
    user_main_buff = user_buff_info['main_buff']
    main_buff_rate_buff = user_main_buff['ratebuff'] if user_main_buff is not None else 0
    number = user_main_buff["number"] if user_main_buff is not None else 0

    leveluprate = int(user_info['level_up_rate'])  # 用户失败次数加成
    # boss战攻击加成
    impart_data = await xiuxian_impart.get_user_info_with_id(user_id)
    boss_atk = impart_data['boss_atk'] if impart_data is not None else 0
    # 当前位置
    now_place = place.get_place_name(await place.get_now_place_id(user_id))

    msg = simple_md(f"道号：{user_fight_info['user_name']}\r"
                    f"气血:{number_to(user_fight_info['fight_hp'])}/{number_to(user_fight_info['max_hp'])}"
                    f"({(user_fight_info['fight_hp'] / user_fight_info['max_hp']) * 100:.2f}%)\r"
                    f"真元:{number_to(user_fight_info['fight_mp'])}/{number_to(user_fight_info['exp'])}"
                    f"({((user_fight_info['fight_mp'] / user_fight_info['exp']) * 100):.2f}%)\r"
                    f"攻击:{number_to(user_fight_info['atk'])}\r"
                    f"突破状态: {exp_meg}\r"
                    f"(概率：{break_rate.get(user_info['level'], 1) + leveluprate + number}%)\r"
                    f"攻击修炼:{user_info['atkpractice']}级\r"
                    f"(提升攻击力{user_info['atkpractice'] * 4}%)\r"
                    f"修炼效率:{int(((level_rate * realm_rate) * (1 + main_buff_rate_buff)) * 100)}%\r"
                    f"会心:{user_fight_info['crit']}%\r"
                    f"减伤率:{(1 - user_fight_info['defence']) * 100:.2f}%\r"
                    f"boss战增益:{int(boss_atk * 100)}%\r"
                    f"会心伤害增益:{int(user_fight_info['burst'] * 100)}%\r"
                    f"当前体力：{user_info['user_stamina']}\r"
                    f"所在位置：{now_place}\r", "日常状态", "日常中心", "查看")
    await sql_message.update_last_check_info_time(user_id)
    await bot.send(event=event, message=msg)
    await mind_state.finish()


@select_state.handle(parameterless=[Cooldown()])
async def select_state_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """查看其他角色状态信息"""

    user_id = await sql_message.get_user_id(args)  # 获取目标id
    if not user_id:
        await bot.send(event=event, message="修仙界中找不到此人！！")
        await select_state.finish()
    await sql_message.update_last_check_info_time(user_id)  # 更新查看修仙信息时间
    user_msg = await sql_message.get_user_real_info(user_id)
    level_rate = await sql_message.get_root_rate(user_msg['root_type'])  # 灵根倍率
    realm_rate = level_data[user_msg['level']]["spend"]  # 境界倍率
    user_buff_data = UserBuffDate(user_id)
    main_buff_data = await user_buff_data.get_user_main_buff_data()
    user_armor_crit_data = await user_buff_data.get_user_armor_buff_data()  # 我的状态防具会心
    user_weapon_data = await UserBuffDate(user_id).get_user_weapon_data()  # 我的状态武器减伤
    user_main_crit_data = await UserBuffDate(user_id).get_user_main_buff_data()  # 我的状态功法会心
    user_main_data = await UserBuffDate(user_id).get_user_main_buff_data()  # 我的状态功法减伤

    if user_main_data is not None:
        main_def = user_main_data['def_buff'] * 100  # 我的状态功法减伤
    else:
        main_def = 0

    if user_armor_crit_data is not None:  # 我的状态防具会心
        armor_crit_buff = ((user_armor_crit_data['crit_buff']) * 100)
    else:
        armor_crit_buff = 0

    if user_weapon_data is not None:
        crit_buff = ((user_weapon_data['crit_buff']) * 100)
    else:
        crit_buff = 0

    user_armor_data = await user_buff_data.get_user_armor_buff_data()
    if user_armor_data is not None:
        def_buff = int(user_armor_data['def_buff'] * 100)  # 我的状态防具减伤
    else:
        def_buff = 0

    if user_weapon_data is not None:
        weapon_def = user_weapon_data['def_buff'] * 100  # 我的状态武器减伤
    else:
        weapon_def = 0

    if user_main_crit_data is not None:  # 我的状态功法会心
        main_crit_buff = ((user_main_crit_data['crit_buff']) * 100)
    else:
        main_crit_buff = 0

    main_buff_rate_buff = main_buff_data['ratebuff'] if main_buff_data is not None else 0
    impart_data = await xiuxian_impart.get_user_info_with_id(user_id)
    impart_know_per = impart_data['impart_know_per'] if impart_data is not None else 0
    impart_burst_per = impart_data['impart_burst_per'] if impart_data is not None else 0
    boss_atk = impart_data['boss_atk'] if impart_data is not None else 0
    weapon_critatk_data = await UserBuffDate(user_id).get_user_weapon_data()  # 我的状态武器会心伤害
    weapon_critatk = weapon_critatk_data['critatk'] if weapon_critatk_data is not None else 0  # 我的状态武器会心伤害
    user_main_critatk = await UserBuffDate(user_id).get_user_main_buff_data()  # 我的状态功法会心伤害
    main_critatk = user_main_critatk['critatk'] if user_main_critatk is not None else 0  # 我的状态功法会心伤害

    msg = f"""
道号：{user_msg['user_name']}
气血:{number_to(user_msg['fight_hp'])}/{number_to(user_msg['max_hp'])}({(user_msg['fight_hp'] / user_msg['max_hp']) * 100:.2f}%)
真元:{number_to(user_msg['fight_mp'])}/{number_to(user_msg['exp'])}({((user_msg['fight_mp'] / user_msg['exp']) * 100):.2f}%)
攻击:{number_to(user_msg['atk'])}
攻击修炼:{user_msg['atkpractice']}级
修炼效率:{int(((level_rate * realm_rate) * (1 + main_buff_rate_buff)) * 100)}%
会心:{crit_buff + int(impart_know_per * 100) + armor_crit_buff + main_crit_buff}%
减伤率:{100 - (((100 - def_buff) * (100 - weapon_def) * (100 - main_def)) / 10000):.2f}%
boss战增益:{int(boss_atk * 100)}%
会心伤害增益:{int((1.5 + impart_burst_per + weapon_critatk + main_critatk) * 100)}%
"""
    await bot.send(event=event, message=msg)
    await select_state.finish()


@buffinfo.handle(parameterless=[Cooldown()])
async def buffinfo_(bot: Bot, event: GroupMessageEvent):
    """我的功法"""

    user_info = await check_user(event)

    user_id = user_info['user_id']
    mainbuffdata = await UserBuffDate(user_id).get_user_main_buff_data()
    if mainbuffdata is not None:
        s, mainbuffmsg = get_main_info_msg(str((await get_user_buff(user_id))['main_buff']))
    else:
        mainbuffmsg = ''

    subbuffdata = await UserBuffDate(user_id).get_user_sub_buff_data()  # 辅修功法13
    if subbuffdata is not None:
        sub, subbuffmsg = get_sub_info_msg(str((await get_user_buff(user_id))['sub_buff']))
    else:
        subbuffmsg = ''

    secbuffdata = await UserBuffDate(user_id).get_user_sec_buff_data()
    secbuffmsg = get_sec_msg(secbuffdata) if get_sec_msg(secbuffdata) != '无' else ''
    msg = simple_md(f"道友的主功法：{mainbuffdata['name'] if mainbuffdata is not None else '无'}\r"
                    f"{mainbuffmsg}\r"
                    f"道友的辅修功法：{subbuffdata['name'] if subbuffdata is not None else '无'}\r"
                    f"{subbuffmsg}\r"
                    f"道友的神通：{secbuffdata['name'] if secbuffdata is not None else '无'}\r"
                    f"{secbuffmsg}\r",
                    "拥有功法", "功法背包", "查看")

    await bot.send(event=event, message=msg)
    await buffinfo.finish()


@del_exp_decimal.handle(parameterless=[Cooldown()])
async def del_exp_decimal_(bot: Bot, event: GroupMessageEvent):
    """清除修为浮点数"""

    user_info = await check_user(event)

    user_id = user_info['user_id']
    exp = user_info['exp']
    await sql_message.del_exp_decimal(user_id, exp)
    msg = f"黑暗动乱暂时抑制成功！"
    await bot.send(event=event, message=msg)
    await del_exp_decimal.finish()


@my_exp_num.handle(parameterless=[Cooldown()])
async def my_exp_num_(bot: Bot, event: GroupMessageEvent):
    """我的双修次数"""
    # 这里曾经是风控模块，但是已经不再需要了
    user_info = await check_user(event)

    user_id = user_info['user_id']
    two_exp_num = await two_exp_cd.find_user(user_id)
    impart_data = await xiuxian_impart.get_user_info_with_id(user_id)
    impart_two_exp = impart_data['impart_two_exp'] if impart_data is not None else 0

    main_two_data = await UserBuffDate(user_id).get_user_main_buff_data()
    main_two = main_two_data['two_buff'] if main_two_data is not None else 0

    num = (two_exp_limit + impart_two_exp + main_two) - two_exp_num
    msg = simple_md(f"道友剩余", "双修", "双修", f"次数{num}次！")
    await bot.send(event=event, message=msg)
    await my_exp_num.finish()


@daily_work.handle(parameterless=[Cooldown()])
async def daily_work_(bot: Bot, event: GroupMessageEvent):
    """我的双修次数"""
    # 这里曾经是风控模块，但是已经不再需要了
    user_info = await check_user(event)

    user_id = user_info['user_id']
    two_exp_num = await two_exp_cd.find_user(user_id)
    impart_data = await xiuxian_impart.get_user_info_with_id(user_id)
    impart_two_exp = impart_data['impart_two_exp'] if impart_data is not None else 0

    main_two_data = await UserBuffDate(user_id).get_user_main_buff_data()
    main_two = main_two_data['two_buff'] if main_two_data is not None else 0

    two_num = (two_exp_limit + impart_two_exp + main_two)
    limit_dict, is_pass = await limit_data.get_limit_by_user_id(user_id)
    impart_pk_num = limit_dict['impart_pk']
    work_num = user_info["work_num"]
    if int(user_info['blessed_spot_flag']) == 0:
        farm = f"无灵田生长中"
    else:
        mix_elixir_info = await get_user_mix_elixir_info(user_id)
        GETCONFIG = {
            "time_cost": 23,  # 单位小时
            "加速基数": 0.10
        }
        last_time = mix_elixir_info['farm_harvest_time']
        if last_time != 0:
            nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # str
            timedeff = round((datetime.strptime(nowtime, '%Y-%m-%d %H:%M:%S')
                              - datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600, 2)
            if timedeff >= round(
                    GETCONFIG['time_cost'] * (1 - (GETCONFIG['加速基数'] * mix_elixir_info['farm_grow_speed'])),
                    2):
                farm = "可收取！！"
            else:
                next_get_time = round(
                    GETCONFIG['time_cost'] * (1 - (GETCONFIG['加速基数'] * mix_elixir_info['farm_grow_speed'])),
                    2) - timedeff
                farm = f"{round(next_get_time, 2)}小时后成熟"
        else:
            farm = '未知生长状态'
    user_tower_info = await tower_handle.check_user_tower_info(user_id)
    if user_tower_info:
        had_get = user_tower_info.get('weekly_point')
        if had_get:
            tower_msg = f"抵达 第{had_get}区域"
        else:
            tower_msg = f"尚未挑战"
    else:
        tower_msg = f"尚未挑战"

    world_boss_info = await get_user_world_boss_info(user_id)
    tips_exp = ''
    if user_info['root_type'] not in ['源宇道根', '道之本源']:
        if user_info['exp'] < 18e10:
            tips_exp = "(被指点)"
    msg = f"今日日常完成情况"
    text = (f"签到 {user_info['is_sign']}/1\r"
            f"体力 {user_info['user_stamina']}/2400\r"
            f"双修{tips_exp} {two_exp_num}/{two_num}\r"
            f"悬赏令 {work_num}/6\r"
            f"虚神界行动 {impart_pk_num}/1\r"
            f"宗门丹药领取 {user_info['sect_elixir_get']}/1\r"
            f"宗门任务完成 {user_info['sect_task']}/4\r"
            f"灵田当前状态 {farm}\r"
            f"本周位面挑战{tower_msg}\r"
            f"今日世界BOSS挑战 {world_boss_info['fight_num']}/3")
    msg = main_md(msg, text,
                  "双修", "双修",
                  "悬赏令", "悬赏令",
                  "宗门丹药领取", "宗门丹药领取",
                  "虚神界帮助", "虚神界帮助")
    await bot.send(event=event, message=msg)
    await daily_work.finish()

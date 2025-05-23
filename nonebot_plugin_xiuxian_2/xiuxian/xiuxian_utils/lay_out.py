import json
import random
import time
from asyncio import get_running_loop
from collections import defaultdict
from enum import IntEnum, auto
from pathlib import Path
from typing import DefaultDict, Dict, Any

from nonebot import require
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import Depends

from .clean_utils import simple_md
from .xiuxian2_handle import sql_message
from ..xiuxian_config import XiuConfig

limit_all_message = require("nonebot_plugin_apscheduler").scheduler
limit_all_stamina = require("nonebot_plugin_apscheduler").scheduler
auto_recover_hp = require("nonebot_plugin_apscheduler").scheduler

limit_all_data: Dict[str, Any] = {}
limit_message_num = XiuConfig().message_limit
limit_message_time = XiuConfig().message_limit_time
cmd_lock = {}
test_user = []

with open(Path(__file__).parent / 'sever_type.json', "r", encoding="UTF-8") as f:
    data = f.read()
sever_mode = json.loads(data)['type']

class UserCmdLock:
    def __init__(self, user_id: int):
        self.user_id = user_id

    def __enter__(self):
        now_time = time.time()
        set_cmd_lock(user_id=self.user_id, lock_time=now_time)

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_cmd_lock(user_id=self.user_id, lock_time=0)


def set_cmd_lock(user_id, lock_time: float | int):
    global cmd_lock
    cmd_lock[int(user_id)] = lock_time


@limit_all_message.scheduled_job('interval', seconds=limit_message_time)
def limit_all_message_():
    # 重置消息字典
    global limit_all_data
    limit_all_data = {}
    logger.opt(colors=True).success(f"<green>已重置消息每{format_time(limit_message_time)}限制！</green>")


@limit_all_stamina.scheduled_job('interval', minutes=1)
async def limit_all_stamina_():
    # 恢复体力
    await sql_message.update_all_users_stamina(XiuConfig().max_stamina, XiuConfig().stamina_recovery_points)


def limit_all_run(user_id: str):
    user_id = str(user_id)
    user_limit_data = limit_all_data.get(user_id)
    if user_limit_data:
        pass
    else:
        limit_all_data[user_id] = {"num": 0,
                                   "tip": False}
    num = limit_all_data[user_id]["num"]
    tip = limit_all_data[user_id]["tip"]
    num += 1
    if num > limit_message_num and tip is False:
        tip = True
        limit_all_data[user_id]["num"] = num
        limit_all_data[user_id]["tip"] = tip
        return True
    if num > limit_message_num and tip is True:
        limit_all_data[user_id]["num"] = num
        return False
    else:
        limit_all_data[user_id]["num"] = num
        return None


def limit_all_run_strong(user_id: str):
    user_id = str(user_id)
    user_limit_data = limit_all_data.get(user_id)
    if user_limit_data:
        pass
    else:
        limit_all_data[user_id] = {"num": 0,
                                   "tip": False}
    num = limit_all_data[user_id]["num"]
    tip = limit_all_data[user_id]["tip"]
    num += 30
    if num > limit_message_num and tip is False:
        tip = True
        limit_all_data[user_id]["num"] = num
        limit_all_data[user_id]["tip"] = tip
        return True
    if num > limit_message_num and tip is True:
        limit_all_data[user_id]["num"] = num
        return False
    else:
        limit_all_data[user_id]["num"] = num
        return None


def format_time(seconds: int) -> str:
    """将秒数转换为更大的时间单位"""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    if days > 0:
        return f"{days}天{hours}小时{minutes}分钟{seconds}秒"
    elif hours > 0:
        return f"{hours}小时{minutes}分钟{seconds}秒"
    elif minutes > 0:
        return f"{minutes}分钟{seconds}秒"
    else:
        return f"{seconds}秒"


def get_random_chat_notice(isolate_level):
    if isolate_level is CooldownIsolateLevel.USER:
        return random.choice([
            "等待{}，让我再歇会！",
            "冷静一下，还有{}，让我再歇会！",
            "时间还没到，还有{}，歇会歇会~~"
        ])
    else:
        return random.choice([
            "该指令忙碌中！！等待{}，让我再歇会！"
        ])


class CooldownIsolateLevel(IntEnum):
    """命令冷却的隔离级别"""

    GLOBAL = auto()
    GROUP = auto()
    USER = auto()
    GROUP_USER = auto()


def Cooldown(
        cd_time: float = 2,
        isolate_level: CooldownIsolateLevel = CooldownIsolateLevel.USER,
        parallel: int = 1,
        stamina_cost: int = 0,
        check_user: bool = True,
        parallel_block: bool = True,
        pass_test_check: bool = False
) -> None:
    """
    依赖注入形式的命令冷却
        cd_time: 命令冷却间隔
        at_sender: 是否at
        isolate_level: 命令冷却的隔离级别, 参考 `CooldownIsolateLevel`
        parallel: 并行执行的命令数量
        stamina_cost: 每次执行命令消耗的体力值
        strong_block: 强阻断
    """
    if not isinstance(isolate_level, CooldownIsolateLevel):
        raise ValueError(
            f"invalid isolate level: {isolate_level!r}, "
            "isolate level must use provided enumerate value."
        )
    running: DefaultDict[str, int] = defaultdict(lambda: parallel)
    time_sy: Dict[str, int] = {}

    def increase(key: str, value: int = 1):
        running[key] += value
        if running[key] >= parallel:
            del running[key]
            del time_sy[key]
        return

    async def dependency(bot: Bot, matcher: Matcher, event: MessageEvent):
        user_id = str(event.get_user_id())
        limit_type = limit_all_run(user_id)
        if user_id in test_user:
            if sever_mode:
                if not pass_test_check:
                    await matcher.finish()
            else:
                too_fast_notice = f"以下为测试服数据，滥用请举报该id：{user_id}"
                await bot.send(event=event, message=too_fast_notice)
        else:
            if not sever_mode:
                if not pass_test_check:
                    await matcher.finish()

        # 发言限制，请前往xiuxian_config设置
        if limit_type is True:
            too_fast_notice = f"道友的指令太迅速了，让我缓会儿！！"
            await bot.send(event=event, message=too_fast_notice)
            await matcher.finish()
        elif limit_type is False:
            await matcher.finish()
        else:
            pass
        if lock_time := cmd_lock.get(user_id):
            if time.time() < (lock_time + 3):
                too_fast_notice = f"道友的指令还在执行中！！"
                await bot.send(event=event, message=too_fast_notice)
                await matcher.finish()
            set_cmd_lock(user_id, 0)

        # 消息长度限制
        message = event.raw_message
        message_len = len(message)
        if message_len > 70:
            too_long_message_notice = f"道友的话也太复杂了，我头好晕！！！"
            await bot.send(event=event, message=too_long_message_notice)
            await matcher.finish()

        loop = get_running_loop()

        if isolate_level is CooldownIsolateLevel.GROUP:
            key = str(
                event.group_id
                if isinstance(event, GroupMessageEvent)
                else event.user_id,
            )
        elif isolate_level is CooldownIsolateLevel.USER:
            key = str(event.user_id)
        elif isolate_level is CooldownIsolateLevel.GROUP_USER:
            key = (
                f"{event.group_id}_{event.user_id}"
                if isinstance(event, GroupMessageEvent)
                else str(event.user_id)
            )
        else:
            key = CooldownIsolateLevel.GLOBAL.name
        if running[key] <= 0:
            if cd_time >= 1.5:
                the_time = int(cd_time - (loop.time() - time_sy[key]))
                if the_time <= 1:
                    the_time = 1
                formatted_time = format_time(the_time)
                await bot.send(event=event,
                               message=get_random_chat_notice(isolate_level).format(formatted_time))
                await matcher.finish()
            else:
                await matcher.finish()
        else:
            time_sy[key] = int(loop.time())
            running[key] -= 1
            loop.call_later(cd_time, lambda: increase(key))
        if parallel_block:
            set_cmd_lock(user_id, time.time())

        # 用户检查

        user_id = int(user_id)
        user_info = await sql_message.get_user_info_with_id(user_id)
        if user_info is None and check_user is True:
            msg = simple_md("修仙界没有道友的信息，请输入", "踏入仙途", "踏入仙途", "加入！")
            await bot.send(event=event, message=msg)
            await matcher.finish()

        if stamina_cost:
            if user_info['user_stamina'] < stamina_cost and XiuConfig().stamina_open is True:
                msg = f"你没有足够的体力，请等待体力恢复后再试！\r本次行动需要消耗：{stamina_cost}体力值\r当前体力值：{user_info['user_stamina']}/2400"
                await bot.send(event=event, message=msg)
                await matcher.finish()
            await sql_message.update_user_stamina(user_id, stamina_cost, 2)  # 减少体力
        return

    return Depends(dependency)

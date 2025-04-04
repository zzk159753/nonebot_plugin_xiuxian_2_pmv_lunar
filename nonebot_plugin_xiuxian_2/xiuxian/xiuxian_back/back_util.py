import operator
import random
from datetime import datetime

from nonebot.adapters.onebot.v11 import MessageSegment

from ..user_data_handle import UserBuffHandle
from ..xiuxian_config import convert_rank, XiuConfig
from ..xiuxian_place import place
from ..xiuxian_utils.clean_utils import encode_base64
from ..xiuxian_utils.item_json import items
from ..xiuxian_utils.xiuxian2_handle import (
    sql_message, UserBuffDate,
    get_weapon_info_msg, get_armor_info_msg,
    get_sec_msg, get_main_info_msg, get_sub_info_msg
)

# 替换模块

YAO_CAI_INFO_MSG = {
    "-1": "性寒",
    "0": "性平",
    "1": "性热",
    "2": "生息",
    "3": "养气",
    "4": "炼气",
    "5": "聚元",
    "6": "凝神",
}


async def get_no_use_equipment_sql(user_id, goods_id):
    """
    卸载装备
    返回sql,和法器或防具
    """
    item_info = items.get_data_by_item_id(goods_id)
    user_buff_info = await UserBuffDate(user_id).buff_info
    now_time = datetime.now()
    sql_str = []
    item_type = ""

    # 检查装备类型，并确定要卸载的是哪种buff
    if item_info['item_type'] == "法器":
        item_type = "法器"
        in_use_id = user_buff_info['faqi_buff']
    elif item_info['item_type'] == "防具":
        item_type = "防具"
        in_use_id = user_buff_info['armor_buff']
    else:
        return sql_str, item_type

    # 如果当前装备正被使用，或者存在需要卸载的其他装备
    if goods_id == in_use_id or in_use_id != 0:
        # 卸载当前装备
        sql_str.append(
            f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 "
            f"WHERE user_id={user_id} and goods_id={goods_id}")
        # 如果还有其他装备需要卸载（对于法器和防具的情况）
        if in_use_id != 0 and goods_id != in_use_id:
            sql_str.append(
                f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 "
                f"WHERE user_id={user_id} and goods_id={in_use_id}")

    return sql_str, item_type


async def check_equipment_use_msg(user_id, goods_id):
    """
    检测装备是否已用
    """
    user_back = await sql_message.get_item_by_good_id_and_user_id(user_id, goods_id)
    state = user_back['state']
    is_use = False
    if state == 0:
        is_use = False
    if state == 1:
        is_use = True
    return is_use


async def get_user_main_back_msg(user_id):
    """
    获取背包内的所有物品信息
    """
    l_equipment_msg = []
    l_skill_msg = []
    l_shenwu_msg = []
    l_xiulianitem_msg = []
    l_libao_msg = []
    l_tdqw_msg = []
    l_tools_msg = []
    l_msg = []
    user_backs = await sql_message.get_back_msg(user_id)  # list(back)
    if user_backs is None:
        return l_msg
    for user_back in user_backs:
        if user_back['goods_type'] == "装备":
            l_equipment_msg = get_equipment_msg(l_equipment_msg, user_back['goods_id'], user_back['goods_num'],
                                                user_back['state'])

        elif user_back['goods_type'] == "技能":
            l_skill_msg = get_skill_msg(l_skill_msg, user_back['goods_id'], user_back['goods_num'])

        elif user_back['goods_type'] == "神物":
            l_shenwu_msg = get_shenwu_msg(l_shenwu_msg, user_back['goods_id'], user_back['goods_num'])

        elif user_back['goods_type'] == "聚灵旗":
            l_xiulianitem_msg = get_jlq_msg(l_xiulianitem_msg, user_back['goods_id'], user_back['goods_num'])

        elif user_back['goods_type'] == "礼包":
            l_libao_msg = get_libao_msg(l_libao_msg, user_back['goods_id'], user_back['goods_num'])

        elif user_back['goods_type'] == "天地奇物":
            l_tdqw_msg = get_tdqw_msg(l_tdqw_msg, user_back['goods_id'], user_back['goods_num'])

        elif user_back['goods_type'] == "道具":
            l_tools_msg = get_tools_msg(l_tools_msg, user_back['goods_id'], user_back['goods_num'])

    if l_equipment_msg:
        top_msg = "☆------我的装备------☆\r" + l_equipment_msg[0]
        l_msg.append(top_msg)
        for msg in l_equipment_msg[1:]:
            l_msg.append(msg)

    if l_skill_msg:
        top_msg = "☆------拥有技能书------☆\r" + l_skill_msg[0]
        l_msg.append(top_msg)
        for msg in l_skill_msg[1:]:
            l_msg.append(msg)

    if l_shenwu_msg:
        top_msg = "☆------神物------☆\r" + l_shenwu_msg[0]
        l_msg.append(top_msg)
        for msg in l_shenwu_msg[1:]:
            l_msg.append(msg)

    if l_xiulianitem_msg:
        top_msg = "☆------修炼物品------☆\r" + l_xiulianitem_msg[0]
        l_msg.append(top_msg)
        for msg in l_xiulianitem_msg[1:]:
            l_msg.append(msg)

    if l_libao_msg:
        top_msg = "☆------礼包------☆\r" + l_libao_msg[0]
        l_msg.append(top_msg)
        for msg in l_libao_msg[1:]:
            l_msg.append(msg)

    if l_tdqw_msg:
        top_msg = "☆------天地奇物------☆\r" + l_tdqw_msg[0]
        l_msg.append(top_msg)
        for msg in l_tdqw_msg[1:]:
            l_msg.append(msg)

    if l_tools_msg:
        top_msg = "☆------持有道具------☆\r" + l_tools_msg[0]
        l_msg.append(top_msg)
        for msg in l_tools_msg[1:]:
            l_msg.append(msg)

    return l_msg


async def get_user_main_back_msg_easy(user_id):
    """
    获取背包内的指定物品信息
    """
    l_msg = []
    item_types = ["装备", "技能", "神物", "聚灵旗", "礼包", "天地奇物", "道具"]
    user_backs = await sql_message.get_back_msg(user_id)  # list(back)
    if user_backs is None:
        return l_msg
    l_types_dict = {}
    for user_back in user_backs:
        goods_type = user_back.get('goods_type')
        if not l_types_dict.get(goods_type):
            l_types_dict[goods_type] = []
        l_types_dict[goods_type].append(user_back)
    l_types_msg_dict = {}
    for item_type in item_types:
        if l_items := l_types_dict.get(item_type):
            l_items.sort(key=lambda k: int(items.get_data_by_item_id(k.get('goods_id')).get('rank')))
            l_items_msg = []
            l_types_sec_dict = {}
            for item in l_items:
                item_info = items.get_data_by_item_id(item['goods_id'])
                item_type_sec = item_info.get('item_type')
                if not l_types_sec_dict.get(item_type_sec):
                    l_types_sec_dict[item_type_sec] = []
                suit_msg = f"{item_info['suits']}·" if 'suits' in item_info else ''
                level = f"{item_info.get('level')} - " if item_info.get('level') else ''
                bind_msg = f"(绑定:{item['bind_num']})" if item['bind_num'] else ""
                l_types_sec_dict[item_type_sec].append(f"{level}{suit_msg}{item['goods_name']} - "
                                                       f"数量：{item['goods_num']}{bind_msg}")
            for item_type_sec, l_items_sec_msg in l_types_sec_dict.items():
                head_msg = f"✨{item_type_sec}✨\r" if item_type_sec != item_type else ''
                top_msg = head_msg + l_items_sec_msg[0]
                l_items_msg.append(top_msg)
                l_items_msg = operator.add(l_items_msg, l_items_sec_msg[1:])
            l_types_msg_dict[item_type] = l_items_msg
    for item_type, l_items_msg in l_types_msg_dict.items():
        top_msg = f"☆------{item_type}------☆\r" + l_items_msg[0]
        l_msg.append(top_msg)
        l_msg = operator.add(l_msg, l_items_msg[1:])
    return l_msg


async def get_user_back_msg(user_id, item_types: list):
    """
    获取背包内的指定物品信息
    """
    l_msg = []
    user_backs = await sql_message.get_back_msg(user_id)  # list(back)
    if user_backs is None:
        return l_msg
    l_types_dict = {}
    for user_back in user_backs:
        goods_type = user_back.get('goods_type')
        if not l_types_dict.get(goods_type):
            l_types_dict[goods_type] = []
        l_types_dict[goods_type].append(user_back)
    l_types_msg_dict = {}
    for item_type in item_types:
        if l_items := l_types_dict.get(item_type):
            l_items.sort(key=lambda k: int(items.get_data_by_item_id(k.get('goods_id')).get('rank')))
            l_items_msg = []
            l_types_sec_dict = {}
            for item in l_items:
                item_info = items.get_data_by_item_id(item['goods_id'])
                item_type_sec = item_info.get('item_type')
                if not l_types_sec_dict.get(item_type_sec):
                    l_types_sec_dict[item_type_sec] = []
                level = f"{item_info.get('level')} - " if item_info.get('level') else ''
                bind_msg = f"(绑定:{item['bind_num']})" if item['bind_num'] else ""
                l_types_sec_dict[item_type_sec].append(f"{level}{item['goods_name']} - "
                                                       f"数量：{item['goods_num']}{bind_msg}")
            for item_type_sec, l_items_sec_msg in l_types_sec_dict.items():
                head_msg = f"✨{item_type_sec}✨\r" if item_type_sec != item_type else ''
                top_msg = head_msg + l_items_sec_msg[0]
                l_items_msg.append(top_msg)
                l_items_msg = operator.add(l_items_msg, l_items_sec_msg[1:])
            l_types_msg_dict[item_type] = l_items_msg
    for item_type, l_items_msg in l_types_msg_dict.items():
        top_msg = f"☆------{item_type}------☆\r" + l_items_msg[0]
        l_msg.append(top_msg)
        l_msg = operator.add(l_msg, l_items_msg[1:])
    return l_msg


async def get_user_skill_back_msg(user_id):
    """
    获取背包内的技能信息, 未使用，并入背包
    """
    l_skill_msg = []
    l_msg = ['道友还未拥有技能书']
    pull_skill = []
    user_backs = await sql_message.get_back_goal_type_msg(user_id, "技能")  # list(back)
    if user_backs is None:
        return l_msg
    for user_back in user_backs:
        if user_back['goods_type'] == "技能":
            l_skill_msg = get_skill_msg(l_skill_msg, user_back['goods_id'], user_back['goods_num'])
    if l_skill_msg:
        pull_skill.append("\r☆------拥有技能书------☆")
        for msg in l_skill_msg:
            pull_skill.append(msg)
    return pull_skill


async def get_user_elixir_back_msg(user_id):
    """
    获取背包内的丹药信息
    """
    l_elixir_msg = []
    l_ldl_msg = []
    l_msg: list = []
    user_backs = await sql_message.get_back_msg(user_id)  # list(back)
    if user_backs is None:
        return l_msg
    for user_back in user_backs:
        if user_back['goods_type'] == "丹药":
            l_elixir_msg = get_elixir_msg(l_elixir_msg, user_back['goods_id'], user_back['goods_num'])
        elif user_back['goods_type'] == "炼丹炉":
            l_ldl_msg = get_ldl_msg(l_ldl_msg, user_back['goods_id'], user_back['goods_num'])

    if l_ldl_msg:
        l_msg.append("☆------炼丹炉------☆")
    for msg in l_ldl_msg:
        l_msg.append(msg)

    if l_elixir_msg:
        l_msg.append("☆------我的丹药------☆")
        for msg in l_elixir_msg:
            l_msg.append(msg)
    return l_msg


async def get_libao_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的礼包信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"名字：{item_info['name']}\r"
    msg += f"拥有数量：{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_tdqw_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的天地奇物信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"名字：{item_info['name']}\r"
    msg += f"介绍：{item_info['desc']}\r"
    msg += f"蕴含天地精华：{item_info['buff']}\r"
    msg += f"拥有数量：{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_tools_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的道具信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"名字：{item_info['name']}\r"
    msg += f"介绍：{item_info['desc']}\r"
    msg += f"拥有数量：{goods_num}"
    l_msg.append(msg)
    return l_msg


async def get_user_yaocai_back_msg(user_id):
    """
    获取背包内的药材信息
    """
    l_yaocai_msg = []
    l_msg = []
    user_backs = await sql_message.get_back_msg(user_id)  # list(back)
    if user_backs is None:
        return l_msg
    level_dict = {"一品药材": 1, "二品药材": 2, "三品药材": 3, "四品药材": 4,
                  "五品药材": 5, "六品药材": 6, "七品药材": 7, "八品药材": 8, "九品药材": 9}
    user_backs.sort(key=lambda k: level_dict.get(items.get_data_by_item_id(k.get('goods_id')).get('level'), 0))
    for user_back in user_backs:
        if user_back['goods_type'] == "药材":
            l_yaocai_msg = get_yaocai_msg(l_yaocai_msg, user_back['goods_id'], user_back['goods_num'])

    if l_yaocai_msg:
        l_msg.append("☆------拥有药材------☆")
        for msg in l_yaocai_msg:
            l_msg.append(msg)
    return l_msg


async def get_user_yaocai_back_msg_easy(user_id):
    """
    获取背包内的药材信息
    """
    l_yaocai_msg = []
    l_msg = []
    user_backs = await sql_message.get_back_msg(user_id)  # list(back)
    level_dict = {"一品药材": 1, "二品药材": 2, "三品药材": 3, "四品药材": 4,
                  "五品药材": 5, "六品药材": 6, "七品药材": 7, "八品药材": 8, "九品药材": 9}
    user_backs.sort(key=lambda k: level_dict.get(
        items.get_data_by_item_id(k.get('goods_id')).get('level'), 0) + 0.01 * len(k.get('goods_name')))
    if user_backs is None:
        return l_msg
    for user_back in user_backs:
        if user_back['goods_type'] == "药材":
            item_info = items.get_data_by_item_id(user_back['goods_id'])
            level = f"{item_info.get('level', '未知品级')[:-2]} - " if item_info.get('level') else ''
            bind_msg = f"(绑定:{user_back['bind_num']})" if user_back['bind_num'] else ""
            l_yaocai_msg.append(f"{level}{user_back['goods_name']} "
                                f"- 数量：{user_back['goods_num']}{bind_msg}")

    if l_yaocai_msg:
        l_msg.append("☆------拥有药材------☆")
        for msg in l_yaocai_msg:
            l_msg.append(msg)
    return l_msg


def get_yaocai_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的药材信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"名字：{item_info['name']}\r"
    msg += f"品级：{item_info['level']}\r"
    msg += get_yaocai_info(item_info)
    msg += f"\r拥有数量:{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_jlq_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的修炼物品信息，聚灵旗
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"名字：{item_info['name']}\r"
    msg += f"效果：{item_info['desc']}"
    msg += f"\r拥有数量:{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_ldl_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的炼丹炉信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"名字：{item_info['name']}\r"
    msg += f"效果：{item_info['desc']}"
    msg += f"\r拥有数量:{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_yaocai_info(yaocai_info):
    """
    获取药材信息
    """
    msg = f"主药 {YAO_CAI_INFO_MSG[str(yaocai_info['主药']['h_a_c']['type'])]}"
    msg += f"{yaocai_info['主药']['h_a_c']['power']}"
    msg += f" {YAO_CAI_INFO_MSG[str(yaocai_info['主药']['type'])]}"
    msg += f"{yaocai_info['主药']['power']}\r"
    msg += f"药引 {YAO_CAI_INFO_MSG[str(yaocai_info['药引']['h_a_c']['type'])]}"
    msg += f"{yaocai_info['药引']['h_a_c']['power']}"
    msg += f"辅药 {YAO_CAI_INFO_MSG[str(yaocai_info['辅药']['type'])]}"
    msg += f"{yaocai_info['辅药']['power']}"

    return msg


def get_equipment_msg(l_msg, goods_id, goods_num, is_use):
    """
    获取背包内的装备信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = ""
    if item_info['item_type'] == '防具':
        msg = get_armor_info_msg(goods_id, item_info)
    elif item_info['item_type'] == '法器':
        msg = get_weapon_info_msg(goods_id, item_info)
    else:
        msg = get_item_msg(goods_id)
    msg += f"\r拥有数量:{goods_num}"
    if is_use:
        msg += f"\r已装备"
    else:
        msg += f"\r可装备"
    l_msg.append(msg)
    return l_msg


def get_skill_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的技能信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = ""
    if item_info['item_type'] == '神通':
        msg = f"{item_info['level']}神通-{item_info['name']}:"
        msg += get_sec_msg(item_info)
    elif item_info['item_type'] == '功法':
        msg = f"{item_info['level']}功法-"
        msg += get_main_info_msg(goods_id)[1]
    elif item_info['item_type'] == '辅修功法':  # 辅修功法12
        msg = f"{item_info['level']}辅修功法-"
        msg += get_sub_info_msg(goods_id)[1]
    msg += f"\r拥有数量:{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_elixir_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的丹药信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"名字：{item_info['name']}\r"
    msg += f"效果：{item_info['desc']}\r"
    msg += f"拥有数量：{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_shenwu_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的神物信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    try:
        desc = item_info['desc']
    except KeyError:
        desc = "这个东西本来会报错让背包出不来，当你看到你背包有这个这个东西的时候请联系超管解决。"

    msg = f"名字：{item_info['name']}\r"
    msg += f"效果：{desc}\r"
    msg += f"拥有数量：{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_item_msg(goods_id, get_image: bool = False):
    """
    获取单个物品的消息
    """
    item_info = items.get_data_by_item_id(goods_id)
    if not item_info:
        return "不存在的物品"
    if item_info['type'] == '丹药':
        msg = f"名字：{item_info['name']}\r"
        msg += f"效果：{item_info['desc']}"

    elif item_info['item_type'] == '神物':
        msg = f"名字：{item_info['name']}\r"
        msg += f"效果：{item_info['desc']}"

    elif item_info['item_type'] == '神通':
        msg = f"名字：{item_info['name']}\r"
        msg += f"品阶：{item_info['level']}\r"
        msg += f"效果：{get_sec_msg(item_info)}"

    elif item_info['item_type'] == '功法':
        msg = f"名字：{item_info['name']}\r"
        msg += f"品阶：{item_info['level']}\r"
        msg += f"效果：{get_main_info_msg(goods_id)[1]}"

    elif item_info['item_type'] == '辅修功法':  # 辅修功法11
        msg = f"名字：{item_info['name']}\r"
        msg += f"品阶：{item_info['level']}\r"
        msg += f"效果：{get_sub_info_msg(goods_id)[1]}"

    elif item_info['item_type'] == '防具':
        msg = get_armor_info_msg(goods_id, item_info)

    elif item_info['item_type'] == '法器':
        msg = get_weapon_info_msg(goods_id, item_info)

    elif item_info['type'] == '装备':
        suits_msg = f"所属套装：{item_info['suits']}\r" if 'suits' in item_info else ''
        effect_msg = '、'.join([f"{increase_name}{'提升' if value > 0 else '降低'}{value * 100:.2f}%"
                               for increase_name, value in item_info['buff'].items()])
        msg = (f"名字：{item_info['name']}\r"
               f"品阶：{item_info['level']}\r"
               f"部位：{item_info['item_type']}\r"
               f"{suits_msg}"
               f"效果：{effect_msg}")

    elif item_info['item_type'] == "药材":
        msg = get_yaocai_info_msg(item_info)

    elif item_info['item_type'] == "聚灵旗":
        msg = f"名字：{item_info['name']}\r"
        msg += f"效果：{item_info['desc']}"

    elif item_info['item_type'] == "炼丹炉":
        msg = f"名字：{item_info['name']}\r"
        msg += f"介绍：{item_info['desc']}"

    elif item_info['item_type'] == "道具":
        msg = f"名字：{item_info['name']}\r"
        msg += f"介绍：{item_info['desc']}"

    elif item_info['item_type'] == "天地奇物":
        msg = f"名字：{item_info['name']}\r"
        msg += f"介绍：{item_info['desc']}\r"
        msg += f"蕴含天地精华：{item_info['buff']}\r"
        msg += ("天地奇物可用于：\r"
                "直接使用：使用后获取奇物内蕴含的天地精华，发送天地精华来获得使用帮助\r"
                "作为素材：除了直接使用外，天地奇物还可用于锻造增强武器，升级丹炉，制造武器，制作防具等等......")
    else:
        msg = '不支持的物品'

    if get_image:
        if 'image_file' in item_info:
            image_base64 = encode_base64(item_info['image_file'])
            print("base64_send")
            return MessageSegment.text(msg) + MessageSegment.image(image_base64)
    return msg


def get_suits_effect(items_name):
    suits_effect_def = {"分身": "召唤继承自身{:.2f}%生命以及攻击的分身协同自身战斗，同类效果数值叠加"}
    msg = (f"套装名称：{items_name}\r"
           f"套装类型：{items.suits[items_name]['套装类型']}\r"
           f"套装介绍：{items.suits[items_name].get('套装介绍', '无')}\r")
    for need_num, suits_buff in items.suits[items_name]['套组效果'].items():
        effect_msg = '\r - '.join([f"{increase_name}{'提升' if value > 0 else '降低'}{value * 100:.2f}%"
                                   if increase_name not in suits_effect_def
                                   else suits_effect_def[increase_name].format(value * 100)
                                   for increase_name, value in suits_buff.items()])
        msg += f"{need_num}件套:\r - {effect_msg}\r"
    include_equipment = [(f"{items.get_data_by_item_id(include_item_id)['item_type']}: "
                          f"{items.get_data_by_item_id(include_item_id)['name']}")
                         for include_item_id in items.suits[items_name]['包含装备']]
    msg += "包含装备：\r - " + '\r - '.join(include_equipment)
    return msg


def get_item_msg_rank(goods_id):
    """
    获取单个物品的rank
    """
    item_info = items.get_data_by_item_id(goods_id)
    if item_info:
        pass
    else:
        return 520
    if item_info['type'] == '丹药':
        msg = item_info['rank']
    elif item_info['type'] == '装备':
        msg = item_info['rank']
    elif item_info['item_type'] == '神通':
        msg = item_info['rank']
    elif item_info['item_type'] == '功法':
        msg = item_info['rank']
    elif item_info['item_type'] == '辅修功法':
        msg = item_info['rank']
    elif item_info['item_type'] == "药材":
        msg = item_info['rank']
    elif item_info['item_type'] == "聚灵旗":
        msg = item_info['rank']
    elif item_info['item_type'] == "炼丹炉":
        msg = item_info['rank']
    else:
        msg = 520
    return int(msg)


def get_yaocai_info_msg(item_info):
    msg = f"名字：{item_info['name']}\r"
    msg += f"品级：{item_info['level']}\r"
    msg += get_yaocai_info(item_info)
    return msg


async def check_use_elixir(user_id, goods_id, num):
    user_info = await sql_message.get_user_info_with_id(user_id)
    user_rank = convert_rank(user_info['level'])[0]
    goods_info = items.get_data_by_item_id(goods_id)
    goods_rank = goods_info['rank']
    goods_name = goods_info['name']
    back = await sql_message.get_item_by_good_id_and_user_id(user_id, goods_id)
    goods_day_num = back['day_num']
    if goods_info['buff_type'] == "level_up_rate":  # 增加突破概率的丹药
        if abs(goods_rank - 55) > user_rank:  # 最低使用限制
            msg = f"丹药：{goods_name}的最低使用境界为{goods_info['境界']}，道友不满足使用条件"
        elif user_rank - abs(goods_rank - 55) > 30:  # 最高使用限制
            msg = f"道友当前境界为：{user_info['level']}，丹药：{goods_name}已不能满足道友，请寻找适合道友的丹药吧！"
        else:  # 检查完毕
            await sql_message.update_back_j(user_id, goods_id, num, 1)
            await sql_message.update_levelrate(user_id, user_info['level_up_rate'] + goods_info['buff'] * num)
            msg = f"道友成功使用丹药：{goods_name}{num}颗，下一次突破的成功概率提高{goods_info['buff'] * num}%!"

    elif goods_info['buff_type'] == "level_up_big":  # 增加大境界突破概率的丹药
        if goods_info['境界'] != user_info['level']:  # 使用限制
            msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}，道友不满足使用条件！"
        else:
            await sql_message.update_back_j(user_id, goods_id, num, 1)
            await sql_message.update_levelrate(user_id, user_info['level_up_rate'] + goods_info['buff'] * num)
            msg = f"道友成功使用丹药：{goods_name}{num}颗,下一次突破的成功概率提高{goods_info['buff'] * num}%!"

    elif goods_info['buff_type'] == "stamina":  # 增加体力的丹药
        if goods_day_num + num > goods_info['day_num']:
            msg = f"道友使用的丹药：{goods_name}{num}颗 超出今日的使用上限({goods_day_num}/{goods_info['day_num']})！！"
        else:  # 检查完毕
            sum_buff = goods_info['buff'] * num
            user_data = await sql_message.get_user_info_with_id(user_id)
            now_stamina = user_data['user_stamina']
            set_stamina = now_stamina + sum_buff
            if set_stamina < XiuConfig().max_stamina:
                await sql_message.update_back_j(user_id, goods_id, num, 1)
                await sql_message.update_user_stamina(user_id, sum_buff, 1)
                msg = f"道友成功使用丹药：{goods_name}{num}颗,恢复体力{sum_buff}!"
            else:
                msg = f"道友当前体力{now_stamina}/{XiuConfig().max_stamina}，使用丹药：{goods_name}{num}颗,将为道友恢复{sum_buff}点体力，超出上限！！！"
            pass

    elif goods_info['buff_type'] == "hp":  # 回复状态的丹药
        if user_info['root'] == "器师":
            user_info = await sql_message.get_user_info_with_id(user_id)
            user_max_hp = int((user_info['exp'] / 2))
            user_max_mp = int(user_info['exp'])
            if user_info['hp'] == user_max_hp and user_info['mp'] == user_max_mp:
                msg = f"道友的状态是满的，用不了哦！"
            else:
                buff = goods_info['buff']
                buff = round((0.016 * user_rank + 0.104) * buff, 2)
                recover_hp = int(buff * user_max_hp * num)
                recover_mp = int(buff * user_max_mp * num)
                user_info = await sql_message.get_user_info_with_id(user_id)
                max_hp = int((user_info['exp'] / 2))
                if user_info['hp'] + recover_hp > max_hp:
                    new_hp = max_hp  # 超过最大
                else:
                    new_hp = user_info['hp'] + recover_hp
                if user_info['mp'] + recover_mp > user_max_mp:
                    new_mp = user_max_mp
                else:
                    new_mp = user_info['mp'] + recover_mp
                msg = f"道友成功使用丹药：{goods_name}{num}颗，经过境界转化状态恢复了{int(buff * 100 * num)}%!"
                await sql_message.update_back_j(user_id, goods_id, num=num, use_key=1)
                await sql_message.update_user_hp_mp(user_id, new_hp, new_mp)
        else:
            if abs(goods_rank - 55) > user_rank:  # 使用限制
                msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
            else:

                user_info = await sql_message.get_user_info_with_id(user_id)
                max_hp = int((user_info['exp'] / 2))
                user_max_mp = int(user_info['exp'])
                if user_info['hp'] == max_hp and user_info['mp'] == user_max_mp:
                    msg = f"道友的状态是满的，用不了哦！"
                else:
                    buff = goods_info['buff']
                    buff = round((180 - user_rank + abs(goods_rank - 55)) / 180 * buff, 2)
                    recover_hp = int(buff * max_hp * num)
                    recover_mp = int(buff * user_max_mp * num)
                    if user_info['hp'] + recover_hp > max_hp:
                        new_hp = max_hp  # 超过最大
                    else:
                        new_hp = user_info['hp'] + recover_hp
                    if user_info['mp'] + recover_mp > user_max_mp:
                        new_mp = user_max_mp
                    else:
                        new_mp = user_info['mp'] + recover_mp
                    msg = f"道友成功使用丹药：{goods_name}{num}颗，经过境界转化状态恢复了{int(buff * 100 * num)}%!"
                    await sql_message.update_back_j(user_id, goods_id, num=num, use_key=1)
                    await sql_message.update_user_hp_mp(user_id, new_hp, new_mp)

    elif goods_info['buff_type'] == "all":  # 回满状态的丹药
        if user_info['root'] == "器师":

            user_info = await sql_message.get_user_info_with_id(user_id)
            user_max_hp = int((user_info['exp'] / 2))

            user_max_mp = int(user_info['exp'])
            if user_info['hp'] == user_max_hp and user_info['mp'] == user_max_mp:
                msg = f"道友的状态是满的，用不了哦！"
            else:
                await sql_message.update_back_j(user_id, goods_id, use_key=1)
                await sql_message.update_user_hp(user_id)
                msg = f"道友成功使用丹药：{goods_name}1颗,状态已全部恢复!"
        else:
            if abs(goods_rank - 55) > user_rank:  # 使用限制
                msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
            else:
                user_info = await sql_message.get_user_info_with_id(user_id)
                user_max_hp = int((user_info['exp'] / 2))
                user_max_mp = int(user_info['exp'])
                if user_info['hp'] == user_max_hp and user_info['mp'] == user_max_mp:
                    msg = f"道友的状态是满的，用不了哦！"
                else:
                    await sql_message.update_back_j(user_id, goods_id, use_key=1)
                    await sql_message.update_user_hp(user_id)
                    msg = f"道友成功使用丹药：{goods_name}1颗,状态已全部恢复!"

    elif goods_info['buff_type'] == "fight_buff":  # 永久加攻击buff的丹药
        if abs(goods_rank - 55) > user_rank:  # 使用限制
            msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
            return msg

        elixir_buff_info = goods_info['buff']
        buff_msg, is_pass = await UserBuffHandle(user_id).add_fight_temp_buff(elixir_buff_info)
        if not is_pass:
            return buff_msg
        await sql_message.update_back_j(user_id, goods_id, num=1, use_key=1)
        msg = f"道友成功使用丹药：{goods_name}1颗，{buff_msg}"

    elif goods_info['buff_type'] == "exp_up":  # 加固定经验值的丹药
        if abs(goods_rank - 55) > user_rank:  # 使用限制
            msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
        else:
            exp = goods_info['buff'] * num
            user_hp = int(user_info['hp'] + (exp / 2))
            user_mp = int(user_info['mp'] + exp)
            user_atk = int(user_info['atk'] + (exp / 10))
            await sql_message.update_exp(user_id, exp)
            await sql_message.update_power2(user_id)  # 更新战力
            await sql_message.update_user_attribute(user_id, user_hp, user_mp, user_atk)  # 这种事情要放在update_exp方法里
            await sql_message.update_back_j(user_id, goods_id, num=num, use_key=1)
            msg = f"道友成功使用丹药：{goods_name}{num}颗,修为增加{exp}点！"
    else:
        msg = f"该类型的丹药目前暂时不支持使用！"
    return msg


async def get_use_jlq_msg(user_id, goods_id):
    user_info = await sql_message.get_user_info_with_id(user_id)
    if user_info['blessed_spot_flag'] == 0:
        msg = f"道友还未拥有洞天福地，无法使用该物品"
    else:
        item_info = items.get_data_by_item_id(goods_id)
        await sql_message.updata_user_blessed_spot_name(user_id, item_info['name'])
        await sql_message.updata_user_blessed_spot(user_id, item_info['修炼速度'])
        msg = f"道友洞天福地的聚灵旗已经替换为：{item_info['name']}"
    return msg


async def get_use_tool_msg(user_id, goods_id, use_num) -> (str, bool):
    """
    使用道具
    :param user_id: 用户ID
    :param goods_id: 物品id
    :param use_num: 使用数量
    :return: 使用结果文本，检查bool
    """
    is_pass = False
    item_info = items.get_data_by_item_id(goods_id)
    user_data = await sql_message.get_user_info_with_id(user_id)
    if item_info['buff_type'] == 1:  # 体力药品
        stamina_buff = int(item_info['buff']) * use_num
        now_stamina = user_data['user_stamina']
        set_stamina = now_stamina + stamina_buff
        if set_stamina < XiuConfig().max_stamina:
            await sql_message.update_user_stamina(user_id, stamina_buff, 1)
            msg = f"使用{item_info['name']}成功，恢复{stamina_buff}点体力！！"
            is_pass = True
        else:
            msg = f"道友当前体力{now_stamina}/{XiuConfig().max_stamina}，{item_info['name']}将为道友恢复{stamina_buff}点体力，超出上限！！！"
        pass
    elif item_info['buff_type'] == 2:
        # 特殊道具
        msg = f"道友成功使用了{item_info['name']}"
        buff_dict = item_info['buff']
        world_change = buff_dict.get('world')
        root_change = buff_dict.get('root_level')
        if world_change is not None:
            place_goal_list = place.get_world_place_list(world_change)
            place_goal = random.choice(place_goal_list)
            await place.set_now_place_id(user_id, place_goal)
            place_name = place.get_place_name(place_goal)
            msg += f"\r霎时间天旋地转,回过神来道友竟被{item_info['name']}带到了【{place_name}】!!!"
        if root_change:
            root_type = await sql_message.update_root(user_id, 8)  # 更换灵根
            msg += f"\r道友丹田一片翻腾，灵根转化为了{root_type}!!!"
        pass
    else:
        msg = f"{item_info['name']}使用失败！！可能暂未开放使用！！！"
    return msg, is_pass

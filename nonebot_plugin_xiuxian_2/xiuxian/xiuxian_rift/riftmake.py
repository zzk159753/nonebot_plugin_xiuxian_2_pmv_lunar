import random

from .riftconfig import get_rift_config
from .skill_rate import skill_rate
from ..user_data_handle import UserBuffHandle
from ..xiuxian_config import convert_rank
from ..xiuxian_utils.item_json import items
from ..xiuxian_utils.other_set import OtherSet
from ..xiuxian_utils.player_fight import boss_fight
from ..xiuxian_utils.utils import number_to
from ..xiuxian_utils.xiuxian2_handle import sql_message

skill_data = skill_rate

NONEMSG = [
    "道友在秘境中晕头转向，等到清醒时竟然发现已被秘境踢出，手中忽多一物，竟是太清明心符！！！",
    "道友进入秘境发现此地烟雾缭绕，无法前行，只能原路返回，归途偶遇一神龛，内里竟藏太清明心符！！！",
]

TREASUREMSG = [
    "道友进入秘境后误入一处兵冢，仔细查探一番后竟然找到了{}",
    "在秘境最深处与神秘势力大战，底牌尽出总算是抢到了{}"
]

TREASUREMSG_1 = [
    "道友进入秘境后闯过了重重试炼，拿到了{}",
    "道友进入秘境后闯过了重重试炼，拿到了{}"
]

TREASUREMSG_2 = [
    "道友进入秘境后偶遇了一位修为深不可测的大能，大能见与你有缘，留下一本{}后飘然离去",
    "道友进入秘境后偶遇了一位修为深不可测的大能，大能见与你有缘，留下一本{}后飘然离去"
]

TREASUREMSG_3 = [
    "道友进入秘境后四处寻宝许久却两手空空，正当秘境快要关闭时你瞥见石缝里的一本灰色书籍，打开一看居然是{}",
    "道友进入秘境后四处寻宝许久却两手空空，正当秘境快要关闭时你瞥见石缝里的一本灰色书籍，打开一看居然是{}"
]

TREASUREMSG_4 = [
    "道友进入秘境后搜刮了一番，{}",
    "道友进入秘境后竟然发现了一位前辈坐化于此，{}"
]

TREASUREMSG_5 = [
    "道友在秘境里探索险境，突然感觉一阵天旋地转，清醒过来时已被踢出秘境！但手里多了一本书籍，竟然是失传已久的{}！",
    "道友在秘境里探索险境，突然感觉一阵天旋地转，清醒过来时已被踢出秘境！但手里多了一本书籍，竟然是失传已久的{}！"
]

STORY = {
    "宝物": {
        "type_rate": 445,
        "功法": {
            "type_rate": 50,
        },
        "辅修功法": {
            "type_rate": 45,
        },
        "神通": {
            "type_rate": 50,
        },
        "法器": {
            "type_rate": 15,
        },
        "防具": {
            "type_rate": 20,
        },
        "新装备": {
            "type_rate": 20,
        },
        "灵石": {
            "type_rate": 10,
            "stone": 20000000
        }
    },
    "战斗": {
        "type_rate": 40,
        "Boss战斗": {
            "Boss数据": {
                "name": ["墨蛟", "婴鲤兽", "千目妖", "鸡冠蛟", "妖冠蛇", "铁火蚁", "天晶蚁", "银光鼠", "紫云鹰",
                         "狗青"],
                "hp": [1.2, 1.4, 1.6, 1.8, 2, 3, 3, 5],
                "mp": 10,
                "atk": [0.1, 0.12, 0.14, 0.16, 0.18, 0.5, 1, 2],
            },
            "success": {
                "desc": "道友大战一番成功战胜{}!",
                "give": {
                    "exp": [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
                            0.01, 0.01, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02,
                            0.01, 0.01, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02,
                            0.01, 0.01, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02,
                            0.01, 0.01, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02,
                            0.02, 0.03, 0.04, 0.03, 0.04, 0.03, 0.04, 0.03, 0.04, 0.03, 0.04, 0.03,
                            0.03, 0.04, 0.03, 0.04, 0.03, 0.04, 0.03, 0.03],
                    "stone": 500000
                }
            },
            "fail": {
                "desc": "道友大战一番不敌{}，仓皇逃窜！",
            }
        },
    },
    "无事": {
        "type_rate": 5,
    },
    "掉血事件": {
        "type_rate": 3,
        "desc": [
            "秘境内竟然散布着浓烈的毒气，道友贸然闯入！{}!",
            "秘境内竟然藏着一群未知势力，道友被打劫了！{}!"
        ],
        "cost": {
            "exp": {
                "type_rate": 25,
                "value": [0.003, 0.004, 0.005, 0.01]
            },
            "hp": {
                "type_rate": 30,
                "value": [0.3, 0.5, 0.7]
            },
            "stone": {
                "type_rate": 25,
                "value": [5000000, 10000000, 15000000]
            },
        }
    }
}


async def get_boss_battle_info(user_info, rift_rank):
    """获取Boss战事件的内容"""
    boss_data = STORY['战斗']['Boss战斗']["Boss数据"]
    player = await UserBuffHandle(user_info['user_id']).get_user_fight_info()
    player['道号'] = player['user_name']
    player['气血'] = player['fight_hp']
    player['攻击'] = player['atk']
    player['真元'] = player['fight_mp']

    base_exp = player['exp']
    boss_info = {
        "name": random.choice(boss_data["name"]),
        "气血": int(base_exp * random.choice(boss_data["hp"])),
        "总血量": int(base_exp * random.choice(boss_data["hp"])),
        "攻击": int(base_exp * random.choice(boss_data["atk"])),
        "真元": base_exp * boss_data["mp"],
        "jj": f"{convert_rank()[1][65][:3]}",
        'stone': 1
    }

    result, victor, bossinfo_new, stone = await boss_fight(player, boss_info)  # 未开启，1不写入，2写入

    if victor == "群友赢了":  # 获胜
        user_rank = convert_rank(user_info['level'])[0]  # 60-用户当前等级 原50
        success_info = STORY['战斗']['Boss战斗']['success']
        msg = success_info['desc'].format(boss_info['name'])
        give_exp = int(random.choice(success_info["give"]["exp"]) * user_info['exp'] * 1.3)
        if user_info['root_type'] not in ['轮回灵根', '源宇道根', '道之本源']:
            if give_exp > 50000000000:
                give_exp = 50000000000
        elif give_exp > 100000000000:
            give_exp = 100000000000
        give_stone = (rift_rank + user_rank) * success_info["give"]["stone"]
        await sql_message.update_exp(user_info['user_id'], give_exp)
        await sql_message.update_ls(user_info['user_id'], give_stone, 1)  # 负数也挺正常
        msg += f"获得了修为：{give_exp}点，灵石：{give_stone}枚！"
    else:  # 输了
        fail_info = STORY['战斗']['Boss战斗']["fail"]
        msg = fail_info['desc'].format(boss_info["name"])
    return result, msg


async def get_dxsj_info(rift_type, user_info):
    """获取掉血事件的内容"""
    msg = None
    cost_type = get_dict_type_rate(STORY[rift_type]['cost'])
    value = random.choice(STORY[rift_type]['cost'][cost_type]['value'])
    if cost_type == "exp":
        exp = min(int(user_info['exp'] * value), 50000000000)
        await sql_message.update_j_exp(user_info['user_id'], exp)

        nowhp = max(user_info['hp'] - (exp / 2), 1)
        nowmp = max(user_info['mp'] - exp, 1)
        await sql_message.update_user_hp_mp(user_info['user_id'], nowhp, nowmp)  # 修为掉了，血量、真元也要掉

        msg = random.choice(STORY[rift_type]['desc']).format(f"修为减少了：{exp}点！")
    elif cost_type == "hp":
        cost_hp = int((user_info['exp'] / 2) * value)
        now_hp = user_info['hp'] - cost_hp
        if now_hp < 0:
            now_hp = 1
        await sql_message.update_user_hp_mp(user_info['user_id'], now_hp, user_info['mp'])
        msg = random.choice(STORY[rift_type]['desc']).format(f"气血减少了：{number_to(cost_hp)}|{cost_hp}点！")
    elif cost_type == "stone":
        cost_stone = value
        await sql_message.update_ls(user_info['user_id'], cost_stone, 2)  # 负数也挺正常
        msg = random.choice(STORY[rift_type]['desc']).format(
            f"灵石减少了：{number_to(cost_stone)}|{cost_stone}枚！")
    return msg


async def get_treasure_info(user_info, rift_rank):
    rift_type = get_goods_type()  # 功法、神通、法器、防具、法宝#todo
    msg = None
    if rift_type == "法器":
        weapon_info = get_weapon(user_info, rift_rank)
        temp_msg = f"{weapon_info[1]['level']}:{weapon_info[1]['name']}!"
        msg = random.choice(TREASUREMSG).format(temp_msg)
        await sql_message.send_back(user_info['user_id'],
                                    weapon_info[0],
                                    weapon_info[1]['name'],
                                    weapon_info[1]['type'], 1,
                                    0)
        # 背包sql

    elif rift_type == "防具":  # todo
        armor_info = get_armor(user_info, rift_rank)
        temp_msg = f"{armor_info[1]['level']}防具：{armor_info[1]['name']}!"
        msg = random.choice(TREASUREMSG_1).format(temp_msg)
        await sql_message.send_back(
            user_info['user_id'],
            armor_info[0],
            armor_info[1]['name'],
            armor_info[1]['type'],
            1, 0)
        # 背包sql

    elif rift_type == "新装备":
        armor_info = get_new_equipment(user_info, rift_rank)
        temp_msg = f"{armor_info[1]['level']}{armor_info[1]['item_type']}：{armor_info[1]['name']}!"
        msg = random.choice(TREASUREMSG_1).format(temp_msg)
        await sql_message.send_back(
            user_info['user_id'],
            armor_info[0],
            armor_info[1]['name'],
            armor_info[1]['type'],
            1, 0)

    elif rift_type == "功法":
        give_main_info = get_main_info(user_info['level'], rift_rank)
        if give_main_info[0]:  # 获得了
            main_buff_id = give_main_info[1]
            print(main_buff_id)
            main_buff = items.get_data_by_item_id(main_buff_id)
            temp_msg = f"{main_buff['level']}功法：{main_buff['name']}"
            msg = random.choice(TREASUREMSG_2).format(temp_msg)
            await sql_message.send_back(user_info['user_id'], main_buff_id, main_buff['name'], main_buff['type'], 1, 0)
        else:
            msg = '道友在秘境中获得一本书籍，翻开一看居然是绿野仙踪...'

    elif rift_type == "神通":
        give_sec_info = get_sec_info(user_info['level'], rift_rank)
        if give_sec_info[0]:  # 获得了
            sec_buff_id = give_sec_info[1]
            sec_buff = items.get_data_by_item_id(sec_buff_id)
            temp_msg = f"{sec_buff['level']}神通：{sec_buff['name']}!"
            msg = random.choice(TREASUREMSG_3).format(temp_msg)
            await sql_message.send_back(user_info['user_id'], sec_buff_id, sec_buff['name'], sec_buff['type'], 1, 0)
            # 背包sql
        else:
            msg = '道友在秘境中获得一本书籍，翻开一看居然是三国演义...'

    elif rift_type == "辅修功法":
        give_sub_info = get_sub_info(user_info['level'], rift_rank)
        if give_sub_info[0]:  # 获得了
            sub_buff_id = give_sub_info[1]
            sub_buff = items.get_data_by_item_id(sub_buff_id)
            temp_msg = f"{sub_buff['level']}辅修功法：{sub_buff['name']}!"
            msg = random.choice(TREASUREMSG_5).format(temp_msg)
            await sql_message.send_back(user_info['user_id'], sub_buff_id, sub_buff['name'], sub_buff['type'], 1, 0)
            # 背包sql
        else:
            msg = '道友在秘境中获得一本书籍，翻开一看居然是四库全书...'

    elif rift_type == "灵石":
        stone_base = STORY['宝物']['灵石']['stone']
        user_rank = random.randint(1, 10)  # 随机等级
        give_stone = (rift_rank + user_rank) * stone_base
        await sql_message.update_ls(user_info['user_id'], give_stone, 1)
        temp_msg = f"竟然获得了灵石：{give_stone}枚！"
        msg = random.choice(TREASUREMSG_4).format(temp_msg)

    return msg


def get_dict_type_rate(data_dict):
    """根据字典内概率,返回字典key"""
    temp_dict = {}
    for i, v in data_dict.items():
        try:
            temp_dict[i] = v["type_rate"]
        except (IndexError, TypeError):
            continue
    key = OtherSet().calculated(temp_dict)
    return key


def get_rift_type():
    """根据概率返回秘境等级"""
    data_dict = get_rift_config()['rift']
    return get_dict_type_rate(data_dict)


def get_story_type():
    """根据概率返回事件类型"""
    data_dict = STORY
    return get_dict_type_rate(data_dict)


def get_battle_type():
    """根据概率返回战斗事件的类型"""
    data_dict = STORY['战斗']
    return get_dict_type_rate(data_dict)


def get_goods_type():
    data_dict = STORY['宝物']
    return get_dict_type_rate(data_dict)


def get_id_by_rank(dict_data, user_level, rift_rank=0):
    """根据字典的rank、用户等级、秘境等级随机获取key"""
    l_temp = []
    final_rank = convert_rank(user_level)[0] + rift_rank  # 秘境等级，会提高用户的等级
    pass_rank = 100  # 最终等级超过次等级会抛弃
    for k, v in dict_data.items():
        if abs(int(v["rank"]) - 55) <= final_rank and (final_rank - abs(int(v["rank"]) - 55)) <= pass_rank:
            l_temp.append(k)
    if not l_temp:
        random.choice(list(dict_data.keys()))
    return random.choice(l_temp)


def get_weapon(user_info, rift_rank=0):
    """
    随机获取一个法器
    :param user_info:用户信息类
    :param rift_rank:秘境等级
    :return 法器ID, 法器信息json
    """
    weapon_data = items.get_data_by_item_type(['法器'])
    weapon_id = get_id_by_rank(weapon_data, user_info['level'], rift_rank)
    weapon_info = items.get_data_by_item_id(weapon_id)
    return weapon_id, weapon_info


def get_armor(user_info, rift_rank=0):
    """
    随机获取一个防具
    :param user_info:用户信息类
    :param rift_rank:秘境等级
    :return 防具ID, 防具信息json
    """
    armor_data = items.get_data_by_item_type(['防具'])
    armor_id = get_id_by_rank(armor_data, user_info['level'], rift_rank)
    armor_info = items.get_data_by_item_id(armor_id)
    return armor_id, armor_info


def get_new_equipment(user_info, rift_rank=0):
    """
    随机获取一个防具
    :param user_info:用户信息类
    :param rift_rank:秘境等级
    :return 防具ID, 防具信息json
    """
    armor_data = items.get_data_by_item_type(["本命法宝",
                                              "辅助法宝",
                                              "内甲",
                                              "道袍",
                                              "道靴",
                                              "灵戒"])
    armor_id = get_id_by_rank(armor_data, user_info['level'], rift_rank)
    armor_info = items.get_data_by_item_id(armor_id)
    return armor_id, armor_info


def get_main_info(user_level, rift_rank):
    """获取功法的信息"""
    main_buff_type = get_skill_by_rank(user_level, rift_rank)  # 天地玄黄
    main_buff_id_list = skill_data[main_buff_type]['gf_list']
    init_rate = 60  # 初始概率为60
    finall_rate = init_rate + rift_rank * 10
    finall_rate = finall_rate if finall_rate <= 100 else 100
    is_success = False
    main_buff_id = 0
    if random.randint(0, 100) <= finall_rate:  # 成功
        is_success = True
        main_buff_id = random.choice(main_buff_id_list)
        return is_success, main_buff_id
    return is_success, main_buff_id


def get_sec_info(user_level, rift_rank):
    """获取神通的信息"""
    sec_buff_type = get_skill_by_rank(user_level, rift_rank)  # 天地玄黄
    sec_buff_id_list = skill_data[sec_buff_type]['st_list']
    init_rate = 60  # 初始概率为60
    finall_rate = init_rate + rift_rank * 10
    finall_rate = finall_rate if finall_rate <= 100 else 100
    is_success = False
    sec_buff_id = 0
    if random.randint(0, 100) <= finall_rate:  # 成功
        is_success = True
        sec_buff_id = random.choice(sec_buff_id_list)
        return is_success, sec_buff_id
    return is_success, sec_buff_id


def get_sub_info(user_level, rift_rank):
    """获取辅修功法的信息"""
    sub_buff_type = get_skill_by_rank(user_level, rift_rank)  # 天地玄黄
    sub_buff_id_list = skill_data[sub_buff_type]['fx_list']
    init_rate = 60  # 初始概率为60
    finall_rate = init_rate + rift_rank * 10
    finall_rate = finall_rate if finall_rate <= 100 else 100
    is_success = False
    sub_buff_id = 0
    if random.randint(0, 100) <= finall_rate:  # 成功
        is_success = True
        sub_buff_id = random.choice(sub_buff_id_list)
        return is_success, sub_buff_id
    return is_success, sub_buff_id


def get_skill_by_rank(user_level, rift_rank):
    """根据用户等级、秘境等级随机获取一个技能"""
    user_rank = convert_rank(user_level)[0]  # type=int，用户等级
    temp_dict = []
    for k, v in skill_data.items():
        if user_rank + rift_rank >= abs(int(v['rank']) - 55):  # 秘境等级会增幅用户等级
            for _ in range(v['type_rate']):
                temp_dict.append(k)
    return random.choice(temp_dict)


class Rift:
    def __init__(self) -> None:
        self.name = ''
        self.place = 0
        self.rank = 0
        self.count = 0
        self.time = 0

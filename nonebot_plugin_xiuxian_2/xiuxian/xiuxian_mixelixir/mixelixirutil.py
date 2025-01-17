import random
from ..xiuxian_utils.item_json import items
from .read_all_mix_elixir_json import all_mix_elixir_table

# 药性定义
herb_value_def = {
    -1: "性寒",
    0: "性平",
    1: "性热",
    2: "生息",
    3: "养气",
    4: "炼气",
    5: "聚元",
    6: "凝神"}


def get_herb_info(herb_id):
    real_herb_info = items.get_data_by_item_id(herb_id)
    herb_info = {
        '药名': real_herb_info['name'],
        '主药': {
            '冷热': real_herb_info['主药']['h_a_c']['type'] * real_herb_info['主药']['h_a_c']['power'],
            '药性': herb_value_def[real_herb_info['主药']['type']],
            '药力': real_herb_info['主药']['power']},
        '药引': {
            '冷热': real_herb_info['药引']['h_a_c']['type'] * real_herb_info['药引']['h_a_c']['power']},
        '辅药': {
            '药性': herb_value_def[real_herb_info['辅药']['type']],
            '药力': real_herb_info['辅药']['power']}}
    return herb_info


def count_mix_param(user_fire_control=None, user_herb_knowledge=None):
    # 计算丹炉温度变化
    if user_fire_control is not None:
        fire_min_param = (int(user_fire_control / (user_fire_control + 5000) * 5)
                          + int(user_fire_control / (user_fire_control + 500) * 3)
                          + int(user_fire_control / (user_fire_control + 100) * 2))

        fire_max_param = (int(user_fire_control / (user_fire_control + 500000) * 15)
                          + int(user_fire_control / (user_fire_control + 50000) * 15)
                          + int(user_fire_control / (user_fire_control + 5000) * 10)
                          + int(user_fire_control / (user_fire_control + 500) * 10))

        base_fire_change = random.randint(10 - fire_min_param, 50 - fire_max_param) * random.choice([1, -1])
    else:
        base_fire_change = 0

    # 丹炉药性变化
    if user_herb_knowledge is not None:
        power_keep_max_param = (int(user_herb_knowledge / (user_herb_knowledge + 5000) * 20)
                                + int(user_herb_knowledge / (user_herb_knowledge + 500) * 10)
                                + int(user_herb_knowledge / (user_herb_knowledge + 100) * 20))

        power_keep_min_param = (int(user_herb_knowledge / (user_herb_knowledge + 500000) * 20)
                                + int(user_herb_knowledge / (user_herb_knowledge + 50000) * 20)
                                + int(user_herb_knowledge / (user_herb_knowledge + 5000) * 20)
                                + int(user_herb_knowledge / (user_herb_knowledge + 500) * 30))
        herb_power_keep = random.randint(10 + power_keep_min_param, 50 + power_keep_max_param)
    else:
        herb_power_keep = 0

    return base_fire_change, herb_power_keep


def count_fire_control(user_fire_control):
    fire_over_improve = (int(user_fire_control / (user_fire_control + 500000) * 30)
                         + int(user_fire_control / (user_fire_control + 50000) * 30)
                         + int(user_fire_control / (user_fire_control + 5000) * 15)
                         + int(user_fire_control / (user_fire_control + 500) * 15))
    return fire_over_improve


class AlchemyFurnace:
    def __init__(self, alchemy_furnace_id):
        # 丹炉属性
        self.alchemy_furnace_id = alchemy_furnace_id
        self.name: str = "无"
        self.fire_sub: int = 0
        self.herb_save: int = 0
        self.make_elixir_improve: int = 0

        # 丹炉状态
        self.fire_value: float = 0
        self.herb_power: dict = {
            "生息": 0,
            "养气": 0,
            "炼气": 0,
            "聚元": 0,
            "凝神": 0}

        # 初始化丹炉属性
        alchemy_furnace_info = items.get_data_by_item_id(alchemy_furnace_id)
        self.name: str = alchemy_furnace_info['name']
        self.fire_sub: int = alchemy_furnace_info['buff']
        self.herb_save: int = alchemy_furnace_info['buff']
        self.make_elixir_improve: int = alchemy_furnace_info['buff']

    def get_sum_herb_power(self) -> int:
        return sum(self.herb_power.values())

    def get_herb_power_rank(self):
        return sorted(self.herb_power, key=lambda x: self.herb_power[x], reverse=True)

    def get_main_herb_power(self):
        if self.get_sum_herb_power():
            herb_power_rank = self.get_herb_power_rank()
            return '、'.join(herb_power_rank[:2])
        else:
            return "无"

    def get_herb_power_msg(self):
        had_herb_power = [f"{herb_power_type}: {round(self.herb_power[herb_power_type], 2)}"
                          for herb_power_type in self.get_herb_power_rank()
                          if self.herb_power[herb_power_type]]
        if not had_herb_power:
            return "当前无药力"
        return "\r".join(had_herb_power)

    def get_state_msg(self) -> str:

        msg = (f"丹炉状态：\r"
               f"丹炉名称：{self.name}\r"
               f"丹火：普通火焰\r"
               f"炉温：{round(self.fire_value, 2)}\r"
               f"炉内总药力：{round(self.get_sum_herb_power(), 2)}\r"
               f"炉内主导药力：{self.get_main_herb_power()}\r"
               f"药力详情：\r"
               f"{self.get_herb_power_msg()}")

        return msg

    def __check_alchemy_furnace_state(self, user_fire_control) -> [str, int]:
        over_fire = self.fire_value - 500

        over_point = abs(over_fire) / (200
                                       + self.fire_sub * 20
                                       + count_fire_control(user_fire_control) * 2)

        if not self.get_sum_herb_power():
            if over_point > 1.5:
                if over_fire > 0:
                    msg = f"\r炉温({self.fire_value})严重超出控制，丹炉发生了爆炸！！"
                    safe_level = 0
                    self.fire_value = random.randint(50, 100)
                else:
                    msg = f"\r炉温({self.fire_value})过低！！请提高温度后加入药材！！"
                    safe_level = 1

            elif over_point > 0.3:
                msg = f"\r当前炉温({self.fire_value})偏"
                msg += '高' if over_fire > 0 else '低'
                msg += ' 不宜加入药材'
                safe_level = 3
            else:
                msg = f"\r当前炉温({self.fire_value})平稳，宜加入药材"
                safe_level = 6
            return msg, safe_level

        if over_point > 1.5:
            if over_fire > 0:
                msg = f"\r炉温({self.fire_value})严重超出控制，丹炉发生了爆炸！！"
                safe_level = 0
                self.fire_value = random.randint(50, 100)
            else:
                msg = f"\r炉温({self.fire_value})严重过低，丹炉内的药液彻底冷凝了！！"
                safe_level = 1
                self.fire_value = max(self.fire_value, 0)
            for herb_type in self.herb_power:
                self.herb_power[herb_type] *= 0.1 * safe_level
            return msg, safe_level
        elif over_point > 1.2:
            # 20% 超出
            msg = f"\r炉温({self.fire_value})超出控制，药性发生了严重流失！！"
            loss_power = over_point - 1
            if over_fire > 0:
                loss_power *= 2
                msg += f"\r药力蒸发流失了{loss_power * 100}%!!"
            else:
                msg += f"\r药力凝固流失了{loss_power * 100}%!!"
            for herb_type in self.herb_power:
                self.herb_power[herb_type] *= 1 - loss_power
            safe_level = 2
        elif over_point > 1:
            # 超出
            loss_power = (over_point - 1) / 2 + 0.1
            if over_fire > 0:
                loss_msg = f"\r药力蒸发流失了{loss_power * 100}%!!"
                loss_type = "高"
            else:
                loss_msg = f"\r药力凝固流失了{loss_power * 100}%!!"
                loss_type = "低"
            for herb_type in self.herb_power:
                self.herb_power[herb_type] *= 1 - loss_power
            msg = f"\r炉温({self.fire_value})过{loss_type}，药性发生了严重流失！！" + loss_msg
            safe_level = 3

        elif over_point > 0.5:
            # 接近超出
            loss_power = 0.1 * over_point / 1
            if over_fire > 0:
                loss_msg = f'\r药力蒸发流失了{loss_power * 100}%!!'
                loss_type = "高"
            else:
                loss_msg = f'\r药力凝固流失了{loss_power * 100}%!!'
                loss_type = "低"
            for herb_type in self.herb_power:
                self.herb_power[herb_type] *= 1 - loss_power
            msg = f"\r炉温({self.fire_value})偏{loss_type}，药性发生了流失！！" + loss_msg
            safe_level = 4

        elif over_point > 0.3:
            if over_fire > 0:
                loss_type = "高"
            else:
                loss_type = "低"
            msg = f'当前炉温({self.fire_value})略{loss_type},道友注意控制丹炉温度！！'
            safe_level = 5

        else:
            msg = f'当前丹炉平稳运行！炉温({self.fire_value})'
            safe_level = 6
        return msg, safe_level

    def __input_herb_as_main(self, user_fire_control, user_herb_knowledge, herb_id, herb_num) -> str:
        herb_info = get_herb_info(herb_id)
        herb_info_main = herb_info['主药']
        herb_fire_change = herb_info_main['冷热'] * herb_num
        herb_type = herb_info_main['药性']
        add_herb_power = herb_info_main['药力'] * herb_num

        # 计算技巧系数
        base_fire_change, herb_power_keep = count_mix_param(user_fire_control=user_fire_control,
                                                            user_herb_knowledge=user_herb_knowledge)

        herb_power_keep_present = herb_power_keep / 100
        herb_fire_change *= herb_power_keep_present
        add_herb_power *= herb_power_keep_present
        self.herb_power[herb_type] += add_herb_power
        self.fire_value = max(self.fire_value + base_fire_change + herb_fire_change, 0)
        result = (f"加入{herb_info['药名']}{herb_num}珠作为主药"
                  f"\r保留{herb_power_keep}%药性({herb_type}:{add_herb_power})")
        if herb_fire_change:
            if herb_fire_change > 0:
                temp_type = '性热'
                temp_change_type = '升高'
            else:
                temp_type = '性寒'
                temp_change_type = '降低'
            result += f"炉温因药材{temp_type}, {temp_change_type}了{herb_fire_change}"
        return result

    def __input_herb_as_ingredient(self, user_fire_control, user_herb_knowledge, herb_id, herb_num) -> str:
        herb_info = get_herb_info(herb_id)
        herb_info_main = herb_info['药引']
        herb_fire_change = herb_info_main['冷热'] * herb_num
        if not herb_fire_change:
            return f"加入{herb_info['药名']}{herb_num}珠作为药引，但无效果"

        # 计算技巧系数
        base_fire_change, herb_power_keep = count_mix_param(user_fire_control=user_fire_control,
                                                            user_herb_knowledge=user_herb_knowledge)

        herb_fire_change = herb_info_main['冷热'] * herb_power_keep / 100

        self.fire_value = max(self.fire_value + base_fire_change + herb_fire_change, 0)
        if herb_fire_change > 0:
            temp_type = '性热'
            temp_change_type = '升高'
        else:
            temp_type = '性寒'
            temp_change_type = '降低'
        result = (f"加入{herb_info['药名']}{herb_num}珠作为药引"
                  f"\r保留{herb_power_keep}%药性({temp_type}:{herb_fire_change})\r"
                  f"炉温因药材{temp_type}, {temp_change_type}了{herb_fire_change}")

        return result

    def __input_herb_as_sub(self, user_fire_control, user_herb_knowledge, herb_id, herb_num) -> str:
        herb_info = get_herb_info(herb_id)
        herb_info_main = herb_info['辅药']
        herb_type = herb_info_main['药性']
        add_herb_power = herb_info_main['药力'] * herb_num

        # 计算技巧系数
        base_fire_change, herb_power_keep = count_mix_param(user_fire_control=user_fire_control,
                                             user_herb_knowledge=user_herb_knowledge)

        herb_power_keep_present = round(herb_power_keep / 100, 2)
        add_herb_power *= herb_power_keep_present
        self.fire_value = max(self.fire_value + base_fire_change, 0)
        # 辅药添加后不超过最大值的80%
        most_herb_type = self.get_herb_power_rank()[0]
        most_herb_power = self.herb_power[most_herb_type] * 0.8
        if herb_type == most_herb_power:
            return f"加入{herb_info['药名']}{herb_num}珠作为辅药\r因为药性没有主药力调和，药性全部流失了"
        real_add_herb_power = min(add_herb_power, most_herb_power - self.herb_power[herb_type])
        self.herb_power[herb_type] = real_add_herb_power
        result = f"加入{herb_info['药名']}{herb_num}珠作为辅药\r保留{herb_power_keep}%药性({herb_type}:{real_add_herb_power})"
        if real_add_herb_power < add_herb_power:
            loss_power = 1 - (real_add_herb_power / add_herb_power)
            result += f"\r由于主药力不足，保留的药性流失了{round(loss_power * 100, 2)}%！！"
        return result

    def input_herbs(self, user_fire_control, user_herb_knowledge, input_herb_list: dict):

        # 记录初始炉温
        start_fire = self.fire_value
        msg = "开始向炉火中添加药材:"

        # 处理主药
        if "主药" in input_herb_list:
            for main_herb in input_herb_list["主药"]:
                msg += "\r" + self.__input_herb_as_main(
                    user_fire_control,
                    user_herb_knowledge,
                    herb_id=main_herb[0],
                    herb_num=main_herb[1])

        # 处理药引
        if "药引" in input_herb_list:
            for main_herb in input_herb_list["药引"]:
                msg += "\r" + self.__input_herb_as_ingredient(
                    user_fire_control,
                    user_herb_knowledge,
                    herb_id=main_herb[0],
                    herb_num=main_herb[1])

        # 处理辅药
        if "辅药" in input_herb_list:
            for main_herb in input_herb_list["辅药"]:
                msg += "\r" + self.__input_herb_as_sub(
                    user_fire_control,
                    user_herb_knowledge,
                    herb_id=main_herb[0],
                    herb_num=main_herb[1])

        fire_change = self.fire_value - start_fire
        msg += f"\r炉温{'升高' if fire_change > 0 else '降低'}了 {abs(fire_change)}!"
        fire_msg, safe_level = self.__check_alchemy_furnace_state(user_fire_control)
        msg += fire_msg
        return msg

    def change_temp(self, user_fire_control, goal_value: int, is_warm_up=True):
        change_type = '升高' if is_warm_up else '降低'
        msg = f"尝试{change_type}{goal_value}点炉温：\r"
        fire_control_param = count_fire_control(user_fire_control)
        random_param = random.randint(10 + fire_control_param, 190 - fire_control_param) / 100
        user_fire_change = random_param * goal_value

        random_fire_change = (random.randint(10 + fire_control_param, 190 - fire_control_param) / 2
                              * random.choice([1, -1]))
        msg += f"{change_type}炉温过程中，丹炉温度波动{'升高' if random_fire_change > 0 else '降低'}了{abs(random_fire_change)}\r"
        msg += f"道友成功使丹炉温度{change_type}了{user_fire_change}\r"
        if not is_warm_up:
            user_fire_change *= -1
        sum_fire_change = user_fire_change + random_fire_change
        msg += f"丹炉总温度{'升高' if sum_fire_change > 0 else '降低'}了{sum_fire_change}\r"
        self.fire_value = max(sum_fire_change + self.fire_value, 0)
        msg += self.__check_alchemy_furnace_state(user_fire_control)[0]
        return msg

    def make_elixir(self):
        herb_power_rank = self.get_herb_power_rank()
        make_elixir_info = {}
        if (herb_power_rank_set := (herb_power_rank[:2]).sort()) not in all_mix_elixir_table:
            msg = f"当前丹炉主导药力对应丹药开发中！！"
            return msg, make_elixir_info
        mix_table = all_mix_elixir_table[herb_power_rank_set]
        now_sum_power = self.get_sum_herb_power()
        msg = f"药力不足，还不足以凝聚丹药！！"
        for elixir_need_power, elixir_id in mix_table.items():
            if now_sum_power > elixir_need_power:
                make_elixir_info = items.get_data_by_item_id(elixir_id)
                make_elixir_info['item_id'] = elixir_id
                msg = f"成功凝聚丹药{make_elixir_info['name']}"
                for herb_type in self.herb_power:
                    self.herb_power[herb_type] = 0
                break
        return msg, make_elixir_info


mix_user: [int, AlchemyFurnace] = {}
